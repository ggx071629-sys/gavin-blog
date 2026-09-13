from __future__ import annotations

import asyncio
import base64
import hmac
import itertools
import math
import os
import struct
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictStr

from ..assistant.owner_lock import ExclusiveFileLock
from .artifact import (
    DIMENSION,
    MAX_TOKENS,
    MODEL,
    REPRESENTATION,
    REVISION,
    VERSION,
    verify_artifact,
)


class EmbeddingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: StrictStr
    input: list[StrictStr] = Field(min_length=1, max_length=1)
    dimensions: Literal[384] = 384
    encoding_format: Literal["float", "base64"] = "float"


class SentenceEncoder:
    def __init__(self, directory: Path) -> None:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        verify_artifact(directory)
        import torch  # type: ignore[import-not-found]  # isolated inference environment
        from sentence_transformers import (  # type: ignore[import-not-found]
            SentenceTransformer,
        )

        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        self.model = SentenceTransformer(
            str(directory),
            device="cpu",
            local_files_only=True,
            trust_remote_code=False,
            model_kwargs={"torch_dtype": torch.float32, "use_safetensors": True},
        )
        self.model.eval()
        from .tokenization import E5Tokenizer

        self.tokenizer = E5Tokenizer(directory)

    def count(self, text: str) -> int:
        return self.tokenizer.count(text)

    def encode(self, text: str) -> list[float]:
        return self.model.encode(
            [text],
            batch_size=1,
            normalize_embeddings=True,
            show_progress_bar=False,
        )[0].tolist()


def identity() -> dict:
    return {
        "model": MODEL,
        "model_version": VERSION,
        "revision": REVISION,
        "dimensions": DIMENSION,
        "max_tokens": MAX_TOKENS,
        "prefix_scheme": "client-query-passage-v1",
        "pooling": "attention-mask-mean",
        "normalization": "l2",
        "representation": REPRESENTATION,
        "concurrency": 1,
        "batch_items": 1,
        "threads": 1,
    }


def create_app(
    *, encoder=None, api_key: str | None = None, queue_size: int = 8, timeout: float = 30
) -> FastAPI:
    secret = api_key or os.environ.get("GAVIN_E5_API_KEY", "")
    if len(secret) < 24:
        raise RuntimeError("GAVIN_E5_API_KEY must contain at least 24 characters")
    if queue_size < 1 or timeout <= 0:
        raise ValueError("invalid queue configuration")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal encoder
        owner = None
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="e5-inference")
        if encoder is None:
            directory = Path(os.environ["GAVIN_E5_MODEL_DIR"]).resolve()
            owner = ExclusiveFileLock(directory / "service.owner.lock")
            owner.acquire()
        try:
            if encoder is None:
                encoder = await asyncio.get_running_loop().run_in_executor(
                    executor,
                    SentenceEncoder,
                    directory,
                )
            queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=queue_size)
            app.state.queue = queue
            app.state.ready = True

            async def consume():
                while True:
                    _priority, _sequence, text, future = await queue.get()
                    try:
                        if not future.cancelled():
                            vector = await asyncio.get_running_loop().run_in_executor(
                                executor,
                                encoder.encode,
                                text,
                            )
                            if not future.done():
                                future.set_result(vector)
                    except Exception:
                        if not future.done():
                            future.set_exception(RuntimeError("embedding inference failed"))
                    finally:
                        queue.task_done()

            worker = asyncio.create_task(consume())
            try:
                yield
            finally:
                app.state.ready = False
                await queue.join()
                worker.cancel()
                await asyncio.gather(worker, return_exceptions=True)
        finally:
            executor.shutdown(wait=True, cancel_futures=True)
            if owner is not None:
                owner.release()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.ready = False
    sequence = itertools.count()

    async def authorize(authorization: str = Header(default="")):
        if not hmac.compare_digest(authorization, "Bearer " + secret):
            raise HTTPException(401, "unauthorized")

    @app.middleware("http")
    async def limit_body(request, call_next):
        from starlette.responses import JSONResponse

        size = 0
        chunks = []
        async for chunk in request.stream():
            size += len(chunk)
            if size > 65536:
                return JSONResponse({"detail": "request body too large"}, status_code=413)
            chunks.append(chunk)
        request._body = b"".join(chunks)
        return await call_next(request)

    @app.get("/healthz")
    async def health():
        return {"status": "alive"}

    @app.get("/readyz", dependencies=[Depends(authorize)])
    async def ready():
        if not app.state.ready:
            raise HTTPException(503, "not ready")
        return identity()

    @app.post("/v1/embeddings", dependencies=[Depends(authorize)])
    async def embeddings(body: EmbeddingRequest):
        if not app.state.ready:
            raise HTTPException(503, "not ready")
        if body.model != MODEL:
            raise HTTPException(400, "model identity mismatch")
        text = body.input[0]
        prefix = "query: " if text.startswith("query: ") else "passage: "
        if not text.startswith(prefix) or not text[len(prefix) :].strip() or "\x00" in text:
            raise HTTPException(400, "input requires a role prefix and nonempty text")
        if len(text) > 16384:
            raise HTTPException(400, "input too long")
        tokens = encoder.count(text)
        if tokens > MAX_TOKENS:
            raise HTTPException(400, "input exceeds 512 tokens; truncation is disabled")
        future = asyncio.get_running_loop().create_future()
        try:
            app.state.queue.put_nowait(
                (0 if prefix == "query: " else 1, next(sequence), text, future)
            )
        except asyncio.QueueFull:
            raise HTTPException(429, "embedding queue full", headers={"Retry-After": "1"}) from None
        try:
            vector = await asyncio.wait_for(future, timeout)
        except TimeoutError:
            raise HTTPException(504, "embedding deadline exceeded") from None
        except RuntimeError:
            raise HTTPException(503, "embedding inference failed") from None
        if (
            len(vector) != DIMENSION
            or not all(math.isfinite(v) for v in vector)
            or abs(sum(v * v for v in vector) - 1.0) > 0.001
        ):
            raise HTTPException(503, "invalid model output")
        value = (
            base64.b64encode(struct.pack("<384f", *vector)).decode("ascii")
            if body.encoding_format == "base64"
            else vector
        )
        return {
            "object": "list",
            **identity(),
            "data": [{"object": "embedding", "index": 0, "embedding": value}],
            "usage": {"prompt_tokens": tokens, "total_tokens": tokens},
        }

    return app
