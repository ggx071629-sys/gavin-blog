"""Run in embedding_service/.venv; compare HTTP output with official mean-pooling formula."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import torch
    import torch.nn.functional as functional
    from transformers import AutoModel, AutoTokenizer

    from app.local_embedding.artifact import MODEL, VERSION, verify_artifact

    directory = Path(os.environ["GAVIN_E5_MODEL_DIR"])
    verify_artifact(directory)
    torch.set_num_threads(1)
    tokenizer = AutoTokenizer.from_pretrained(directory, local_files_only=True)
    model = AutoModel.from_pretrained(directory, local_files_only=True, use_safetensors=True)
    model.eval()
    texts = [
        "query: 作者有哪些技术项目？",
        "query: What technologies does the author use?",
        "passage: 本站项目采用 FastAPI、SQLite 与 Nuxt。",
        "passage: The application uses immutable published revisions and hybrid retrieval.",
    ]
    errors = []
    tokens = []
    timings = []
    for text in texts:
        inputs = tokenizer([text], return_tensors="pt", truncation=False)
        with torch.inference_mode():
            hidden = model(**inputs).last_hidden_state
            hidden = hidden.masked_fill(~inputs["attention_mask"][..., None].bool(), 0.0)
            mean = hidden.sum(dim=1) / inputs["attention_mask"].sum(dim=1)[..., None]
            expected = functional.normalize(mean, p=2, dim=1)[0]
        request = urllib.request.Request(
            "http://127.0.0.1:8091/v1/embeddings",
            data=json.dumps({"model": MODEL, "input": [text], "dimensions": 384}).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + os.environ["GAVIN_E5_API_KEY"],
            },
        )
        start = time.perf_counter()
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.load(response)
        timings.append(time.perf_counter() - start)
        actual = torch.tensor(data["data"][0]["embedding"])
        error = float(torch.max(torch.abs(actual - expected)))
        assert error < 1e-5
        assert data["model_version"] == VERSION
        assert data["usage"]["prompt_tokens"] == int(inputs["attention_mask"].sum())
        tokens.append(data["usage"]["prompt_tokens"])
        errors.append(error)
    print(
        json.dumps(
            {
                "model": MODEL,
                "version": VERSION,
                "reference_max_abs_errors": errors,
                "actual_tokens": tokens,
                "request_seconds": timings,
                "platform_scope": "local-development-only",
            }
        )
    )


if __name__ == "__main__":
    main()
