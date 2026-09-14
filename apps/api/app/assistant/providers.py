from __future__ import annotations

import hashlib
import html
import json
import math
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, convert_to_messages
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, SecretStr

from ..assistant_index.constants import TEST_EMBEDDING_MODEL, TEST_EMBEDDING_MODEL_VERSION
from ..assistant_index.embeddings import DeterministicHashEmbeddings
from ..config import Settings
from ..search import markdown_to_plain_text
from .constants import (
    PROVIDER_OPENAI_COMPATIBLE,
    PROVIDER_TEST,
    TEST_CHAT_MODEL,
    TEST_CHAT_MODEL_VERSION,
)
from .quote_refs import SOURCE_LABELS, SOURCE_LABELS_EN, render_quote, resolve_quotes


class AnswerSupport(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    citation_id: str
    quote: str = Field(min_length=1, max_length=1200)


class AnswerBlock(BaseModel):
    text: str
    citation_ids: list[str] = Field(default_factory=list)
    supports: list[AnswerSupport] = Field(default_factory=list, max_length=8)


class ModelAnswer(BaseModel):
    blocks: list[AnswerBlock]


class _JsonAnswerBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    text: str
    citation_ids: list[str]
    supports: list[AnswerSupport] = Field(max_length=8)


class _JsonAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    blocks: list[_JsonAnswerBlock]


class _ReferenceSupport(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    citation_id: str
    quote_id: str = Field(min_length=1, max_length=64)


class _ReferenceBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    text: str
    citation_ids: list[str]
    supports: list[_ReferenceSupport] = Field(max_length=8)


class _ReferenceAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    blocks: list[_ReferenceBlock]


class _SelectionBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    citation_ids: list[str] = Field(min_length=1)
    supports: list[_ReferenceSupport] = Field(min_length=1, max_length=8)


class _SelectionAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    blocks: list[_SelectionBlock]


def answer_schema_instruction(
    reference_mode: bool = False, extractive: bool = False, single_command: bool = False,
) -> str:
    schema = _JsonAnswer.model_json_schema()
    if reference_mode:
        support = schema['$defs']['AnswerSupport']
        support['properties'].pop('quote')
        support['properties']['quote_id'] = dict(type='string', minLength=1, maxLength=64)
        support['required'] = ['citation_id', 'quote_id']
    if extractive:
        block = schema['$defs']['_JsonAnswerBlock']
        block['properties'].pop('text')
        block['required'].remove('text')
        block['properties']['supports'].update(minItems=1, maxItems=1)
        block['properties']['citation_ids'].update(minItems=1, maxItems=1)
    if single_command:
        schema['properties']['blocks']['maxItems'] = 1
    quote_example = ('"quote_id":"@q:c1:0"' if reference_mode
                     else '"quote":"Complete source clause."')
    return (
        "Return one complete JSON object matching this schema. No markdown fences or "
        "additional fields. Schema keywords (additionalProperties, properties, type, required) "
        "are rules, NEVER data fields. "
        + ('Choose complete source quotes answering the question; the server displays them. '
           if extractive else '')
        + 'Data shape example only: {"blocks":[{'
        + ('' if extractive else '"text":"Complete source clause.",')
        +
        '"citation_ids":["c1"],"supports":[{"citation_id":"c1",'
        + quote_example + '}]}]}. Replace example values with actual evidence. '
        "Cite only provided evidence aliases. When the evidence cannot "
        'answer the question, return {"blocks":[]} without inventing an answer. JSON schema: '
        + json.dumps(schema, sort_keys=True, separators=(",", ":"))
    )


class LocalDeepSeekChatOpenAI(ChatOpenAI):
    """DeepSeek JSON wire adapter; legacy class name retained for local ledgers."""

    _evaluation_guard: Any = PrivateAttr(default=None)

    def assistant_envelope_token_count(self, text: str) -> int:
        if self.model_name != 'deepseek-flash':
            raise ValueError('no pinned tokenizer for this model')
        from .deepseek_tokenizer import token_ids

        return len(token_ids(text))

    def _get_request_payload(self, input_: Any, *, stop=None, **kwargs: Any) -> dict:
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        # ChatOpenAI normalizes max_tokens to max_completion_tokens internally.
        # Translate at the final wire boundary for both sync and async calls.
        payload["max_tokens"] = payload.pop("max_completion_tokens")
        payload["extra_body"] = {"thinking": {"type": "disabled"}}
        if payload.get("response_format") == {"type": "json_object"}:
            # Keep the wire field, but use SDK create rather than parse: parse
            # raises on length/content_filter before returning billable usage.
            payload["extra_body"]["response_format"] = payload.pop("response_format")
        return payload


def bind_answer_model(chat: BaseChatModel) -> Any:
    if not isinstance(chat, LocalDeepSeekChatOpenAI):
        return chat.with_structured_output(
            ModelAnswer,
            method="json_schema",
            strict=True,
            include_raw=True,
        )

    def prepare(messages: Any) -> list[BaseMessage]:
        converted = convert_to_messages(messages)
        refs = bool(getattr(messages, 'quotes', {}))
        policies = [answer_schema_instruction(
            refs, refs and (not getattr(messages, 'answer_in_english', False)
                          or getattr(messages, 'single_command', False)),
            getattr(messages, 'single_command', False),
        )]
        for message in converted:
            if isinstance(message, SystemMessage):
                if not isinstance(message.content, str):
                    raise ValueError('system policy must be text')
                policies.append(message.content)
        return [SystemMessage(content='\n\n'.join(policies)),
                *(m for m in converted if not isinstance(m, SystemMessage))]

    def validate(
        result: dict[str, Any], quotes: dict, english_command: bool, labels: dict[str, str],
    ) -> dict[str, Any]:
        raw = result.get("raw")
        try:
            # Re-parse the complete original content. LangChain's JSON parser can
            # repair partial JSON or strip fences, which we must never accept.
            if not isinstance(raw, AIMessage) or not isinstance(raw.content, str):
                raise ValueError("missing text response")
            try:
                answer = _JsonAnswer.model_validate_json(raw.content, strict=True)
                parsed = resolve_quotes(ModelAnswer.model_validate(answer.model_dump()), quotes)
            except ValueError:
                if not quotes:
                    raise
                try:
                    referenced = _ReferenceAnswer.model_validate_json(raw.content, strict=True)
                    data = referenced.model_dump()
                except ValueError:
                    selected = _SelectionAnswer.model_validate_json(raw.content, strict=True)
                    data = {'blocks': []}
                    seen_quotes = set()
                    for selected_block in selected.model_dump()['blocks']:
                        if set(selected_block['citation_ids']) != {
                            s['citation_id'] for s in selected_block['supports']
                        }:
                            raise ValueError('selection source mismatch') from None
                        for support in selected_block['supports']:
                            entry = quotes.get(support['quote_id'])
                            if entry is None or entry[0] != support['citation_id']:
                                raise ValueError('unknown/cross-source quote selection') from None
                            project_key = getattr(quotes, 'projects', {}).get(support['quote_id'])
                            if project_key and project_key not in seen_quotes:
                                project_alias, project_quote = quotes[project_key]
                                data['blocks'].append(dict(
                                    text=render_quote(project_quote), citation_ids=[project_alias],
                                    supports=[dict(
                                        citation_id=project_alias, quote_id=project_key,
                                    )],
                                ))
                                seen_quotes.add(project_key)
                            if support['quote_id'] in seen_quotes:
                                continue
                            seen_quotes.add(support['quote_id'])
                            data['blocks'].append(dict(
                                text=render_quote(entry[1], english_command),
                                citation_ids=[support['citation_id']], supports=[support],
                            ))
                for block in data['blocks']:
                    for support in block['supports']:
                        support['quote'] = support.pop('quote_id')
                        if not support['quote'].startswith('@q:'):
                            raise ValueError('invalid quote reference') from None
                parsed = resolve_quotes(ModelAnswer.model_validate(data), quotes)
            for block in parsed.blocks:
                source_labels = {labels.get(getattr(quotes, 'source_types', {}).get(cid, ''), '')
                                 for cid in block.citation_ids}
                if len(source_labels) == 1 and (label := next(iter(source_labels))):
                    if not block.text.startswith(label):
                        block.text = label + block.text
        except ValueError:
            return {"raw": raw, "parsed": None, "parsing_error": "invalid_answer_schema"}
        return {"raw": raw, "parsed": parsed, "parsing_error": None}

    bound = chat.with_structured_output(_JsonAnswer, method="json_mode", include_raw=True)
    wire = RunnableLambda(prepare) | bound

    def call(messages):
        return validate(wire.invoke(messages), getattr(messages, 'quotes', {}),
                        getattr(messages, 'single_command', False),
                        (SOURCE_LABELS_EN if getattr(messages, 'answer_in_english', False)
                         else SOURCE_LABELS) if getattr(messages, 'personal_skills', False) else {})

    async def acall(messages):
        return validate(await wire.ainvoke(messages), getattr(messages, 'quotes', {}),
                        getattr(messages, 'single_command', False),
                        (SOURCE_LABELS_EN if getattr(messages, 'answer_in_english', False)
                         else SOURCE_LABELS) if getattr(messages, 'personal_skills', False) else {})

    chain = RunnableLambda(call, afunc=acall)
    return chat._evaluation_guard.wrap(chain, chat) if chat._evaluation_guard else chain


@dataclass(frozen=True)
class EmbeddingUsage:
    vectors: list[list[float]]
    input_tokens: int | None
    usage_source: str
    model: str
    model_identity_source: str
    version: str
    version_identity_source: str

    @property
    def vector(self) -> list[float]:
        return self.vectors[0]


class MeteredEmbeddings(Embeddings):
    """Embeddings adapter that preserves usage for billing ledgers."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embed_documents_metered(texts).vectors

    def embed_query(self, text: str) -> list[float]:
        return self.embed_query_metered(text).vector

    def embed_documents_metered(self, texts: list[str]) -> EmbeddingUsage:
        raise NotImplementedError

    def embed_query_metered(self, text: str) -> EmbeddingUsage:
        return self.embed_documents_metered([text])


class DeterministicMeteredEmbeddings(MeteredEmbeddings):
    def __init__(self, inner: DeterministicHashEmbeddings) -> None:
        self.inner = inner
        self.calls: list[str] = []

    def embed_documents_metered(self, texts: list[str]) -> EmbeddingUsage:
        self.calls.extend(texts)
        vectors = self.inner.embed_documents(texts)
        tokens = sum(max(1, math.ceil(len(text) / 4)) for text in texts)
        return EmbeddingUsage(
            vectors=vectors,
            input_tokens=tokens,
            usage_source="deterministic-test-adapter",
            model=self.inner.model,
            model_identity_source="deterministic-test-adapter",
            version=self.inner.version,
            version_identity_source="deterministic-test-adapter",
        )


class DevelopmentLexicalEmbeddings(DeterministicHashEmbeddings):
    """Offline feature-hash embeddings with useful lexical locality for development."""

    def _embed(self, text: str) -> list[float]:
        normalized = html.unescape(text).casefold()
        features: set[tuple[str, int]] = set()
        for word in re.findall(r"[a-z0-9][a-z0-9_-]*", normalized):
            features.add((f"word:{word}", max(2, min(len(word), 8))))
        for run in re.findall(r"[\u3400-\u9fff]+", normalized):
            if len(run) == 1:
                features.add((f"cjk:{run}", 1))
            for size in range(2, min(4, len(run)) + 1):
                for offset in range(len(run) - size + 1):
                    features.add((f"cjk:{run[offset : offset + size]}", size))
        if not features:
            return super()._embed(text)
        values = [0.0] * self.dimension
        for feature, weight in features:
            digest = hashlib.sha256(f"{self.model}:{self.version}:{feature}".encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] & 1 else -1.0
            values[index] += sign * weight
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]


class OpenAICompatibleMeteredEmbeddings(MeteredEmbeddings):
    def __init__(
        self,
        *,
        model: str,
        version: str,
        api_key: str,
        base_url: str,
        dimension: int,
        timeout: float,
        max_batch_items: int,
        ca_file: str | None = None,
    ) -> None:
        self.model = model
        self.version = version
        self.dimension = dimension
        self.max_batch_items = max_batch_items
        import ssl

        from openai import DefaultHttpxClient

        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=0,
            timeout=timeout,
            http_client=(
                DefaultHttpxClient(verify=ssl.create_default_context(cafile=ca_file))
                if ca_file else None
            ),
        )

    def embed_documents_metered(self, texts: list[str]) -> EmbeddingUsage:
        return self._request_metered(texts)

    def _request_metered(self, texts: list[str]) -> EmbeddingUsage:
        if not texts:
            return EmbeddingUsage(
                vectors=[],
                input_tokens=0,
                usage_source="provider-response",
                model=self.model,
                model_identity_source="operator-declaration",
                version=self.version,
                version_identity_source="operator-declaration",
            )
        vectors: list[list[float]] = []
        total_tokens = 0
        usage_proven = True
        reported_models: set[str] = set()
        for offset in range(0, len(texts), self.max_batch_items):
            batch = texts[offset : offset + self.max_batch_items]
            response = self._client.embeddings.create(
                model=self.model,
                input=batch,
                dimensions=self.dimension,
                encoding_format="float",
            )
            batch_vectors = [item.embedding for item in response.data]
            if len(batch_vectors) != len(batch):
                raise RuntimeError("embedding provider returned the wrong vector count")
            if any(
                len(vector) != self.dimension
                or not all(math.isfinite(float(value)) for value in vector)
                for vector in batch_vectors
            ):
                raise RuntimeError("embedding provider returned an invalid vector")
            vectors.extend(batch_vectors)
            usage = getattr(response, "usage", None)
            tokens = int(
                getattr(usage, "prompt_tokens", 0) or getattr(usage, "input_tokens", 0) or 0
            )
            if tokens <= 0:
                usage_proven = False
            else:
                total_tokens += tokens
            reported_model = str(getattr(response, "model", "") or "").strip()
            if reported_model:
                reported_models.add(reported_model)
        model_proven = len(reported_models) == 1
        return EmbeddingUsage(
            vectors=vectors,
            input_tokens=total_tokens if usage_proven else None,
            usage_source="provider-response" if usage_proven else "unknown",
            model=next(iter(reported_models)) if model_proven else self.model,
            model_identity_source="provider-response" if model_proven else "operator-declaration",
            version=self.version,
            version_identity_source="operator-declaration",
        )


@dataclass
class ScriptedChatTurn:
    parsed: dict[str, Any]
    finish_reason: str = "stop"
    input_tokens: int = 20
    output_tokens: int = 40
    parsing_error: str | None = None


class DeterministicChatModel(BaseChatModel):
    """Offline structured-output double. Not a production chat provider."""

    _script: list[ScriptedChatTurn] = PrivateAttr(default_factory=list)
    _calls: list[list[BaseMessage]] = PrivateAttr(default_factory=list)
    _hold: Any = PrivateAttr(default=None)
    _hold_loop: Any = PrivateAttr(default=None)
    _started: Any = PrivateAttr(default=None)

    def hold(self) -> None:
        import asyncio
        import threading

        self._hold = asyncio.Event()
        self._started = threading.Event()

    def wait_until_started(self, timeout: float = 5.0) -> bool:
        return bool(self._started is not None and self._started.wait(timeout))

    def release(self) -> None:
        if self._hold is not None:
            if self._hold_loop is not None:
                self._hold_loop.call_soon_threadsafe(self._hold.set)
            else:
                self._hold.set()

    @property
    def script(self) -> list[ScriptedChatTurn]:
        return self._script

    @property
    def calls(self) -> list[list[BaseMessage]]:
        return self._calls

    @property
    def _llm_type(self) -> str:
        return "deterministic-assistant-chat"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        turn = self._next(messages)
        message = AIMessage(
            content=json.dumps(turn.parsed, ensure_ascii=False),
            response_metadata={
                "finish_reason": turn.finish_reason,
                "token_usage": {
                    "prompt_tokens": turn.input_tokens,
                    "completion_tokens": turn.output_tokens,
                    "total_tokens": turn.input_tokens + turn.output_tokens,
                },
                "model_name": TEST_CHAT_MODEL,
            },
            usage_metadata={
                "input_tokens": turn.input_tokens,
                "output_tokens": turn.output_tokens,
                "total_tokens": turn.input_tokens + turn.output_tokens,
            },
        )
        return ChatResult(generations=[ChatGeneration(message=message)])

    def _next(self, messages: list[BaseMessage]) -> ScriptedChatTurn:
        self._calls.append(list(messages))
        if self._script:
            return self._script.pop(0)
        # Default offline reply derives its support from the actual prompt.
        human = str(getattr(messages[-1], "content", messages[-1][1]
                    if isinstance(messages[-1], tuple) else "")) if messages else ""
        match = _DEVELOPMENT_EVIDENCE_RE.search(human)
        if not match:
            return ScriptedChatTurn(parsed={"blocks": []})
        descriptor = json.loads(html.unescape(match.group(1)))
        quote = html.unescape(match.group(2)).strip()[:1200]
        return ScriptedChatTurn(
            parsed={
                "blocks": [
                    {
                        "text": markdown_to_plain_text(quote),
                        "citation_ids": [descriptor["id"]],
                        "supports": [{"citation_id": descriptor["id"], "quote": quote}],
                    }
                ]
            }
        )

    def assistant_token_count(self, text: str) -> int:
        return max(1, (len(text.encode("utf-8")) + 3) // 4)

    def with_structured_output(self, schema, **kwargs):
        if kwargs.get("method") != "json_schema" or kwargs.get("strict") is not True:
            raise RuntimeError("structured output must use json_schema strict mode")
        if kwargs.get("include_raw") is not True:
            raise RuntimeError("structured output must include raw envelopes")
        parent = self

        class _Structured:
            def invoke(self, messages, **_kwargs):
                return self._finish(parent._next(list(messages)))

            async def ainvoke(self, messages, **_kwargs):
                import asyncio

                hold = parent._hold
                if hold is not None:
                    parent._hold_loop = asyncio.get_running_loop()
                    if parent._started is not None:
                        parent._started.set()
                    await hold.wait()
                return self._finish(parent._next(list(messages)))

            def _finish(self, turn: ScriptedChatTurn):
                raw = AIMessage(
                    content=json.dumps(turn.parsed, ensure_ascii=False),
                    response_metadata={
                        "finish_reason": turn.finish_reason,
                        "model_name": TEST_CHAT_MODEL,
                        "model_version": TEST_CHAT_MODEL_VERSION,
                        "token_usage": {
                            "prompt_tokens": turn.input_tokens,
                            "completion_tokens": turn.output_tokens,
                            "total_tokens": turn.input_tokens + turn.output_tokens,
                        },
                    },
                    usage_metadata={
                        "input_tokens": turn.input_tokens,
                        "output_tokens": turn.output_tokens,
                        "total_tokens": turn.input_tokens + turn.output_tokens,
                    },
                )
                parsed = None if turn.parsing_error else schema.model_validate(turn.parsed)
                return {
                    "raw": raw,
                    "parsed": parsed,
                    "parsing_error": turn.parsing_error,
                }

        return _Structured()


_DEVELOPMENT_EVIDENCE_RE = re.compile(
    r"<untrusted-evidence descriptor=(\{.*?\})>\n(.*?)\n</untrusted-evidence>",
    re.DOTALL,
)
_DEVELOPMENT_QUESTION_RE = re.compile(
    r"<current-question>(.*?)</current-question>",
    re.DOTALL,
)


def _development_relevance(question: str, evidence: str) -> int:
    question = html.unescape(question).casefold()
    evidence = html.unescape(evidence).casefold()
    score = 0
    for word in set(re.findall(r"[a-z0-9][a-z0-9_-]*", question)):
        if len(word) >= 2 and word in evidence:
            score += min(len(word), 8) ** 2
    for run in re.findall(r"[\u3400-\u9fff]+", question):
        for size in range(2, min(4, len(run)) + 1):
            for offset in range(len(run) - size + 1):
                feature = run[offset : offset + size]
                if feature in evidence:
                    score += size * size
    return score


class DevelopmentEvidenceChatModel(DeterministicChatModel):
    """Offline development adapter that turns retrieved evidence into cited excerpts."""

    def _next(self, messages: list[BaseMessage]) -> ScriptedChatTurn:
        self._calls.append(list(messages))
        if self._script:
            return self._script.pop(0)
        human = ""
        for message in reversed(messages):
            if isinstance(message, tuple) and len(message) == 2 and message[0] == "human":
                human = str(message[1])
                break
            if getattr(message, "type", None) == "human":
                human = str(message.content)
                break
        question_match = _DEVELOPMENT_QUESTION_RE.search(human)
        question = question_match.group(1) if question_match else ""
        ranked: list[tuple[int, int, dict[str, Any], str]] = []
        raw_quotes: dict[str, str] = {}
        for index, (raw_descriptor, raw_body) in enumerate(_DEVELOPMENT_EVIDENCE_RE.findall(human)):
            descriptor = json.loads(html.unescape(raw_descriptor))
            body = markdown_to_plain_text(html.unescape(raw_body))
            body = re.sub(r"\[[1-9][0-9]*\]", "", body)
            body = re.sub(r"javascript:", "javascript ", body, flags=re.IGNORECASE)
            citation_id = str(descriptor.get("id") or "").strip()
            if not body or not citation_id:
                continue
            raw_quotes[citation_id] = html.unescape(raw_body).strip()[:1200]
            searchable = " ".join(
                (
                    body,
                    str(descriptor.get("path") or ""),
                    str(descriptor.get("heading") or ""),
                )
            )
            ranked.append((_development_relevance(question, searchable), index, descriptor, body))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        blocks: list[dict[str, Any]] = []
        grouped: dict[str, dict[str, Any]] = {}
        for score, _index, descriptor, body in ranked:
            if score <= 0:
                continue
            citation_id = str(descriptor["id"])
            source_key = str(descriptor.get("path") or citation_id)
            if source_key not in grouped:
                grouped[source_key] = {
                    "score": score,
                    "citation_id": citation_id,
                    "bodies": [],
                }
            grouped[source_key]["score"] = max(grouped[source_key]["score"], score)
            if len(grouped[source_key]["bodies"]) < 2:
                grouped[source_key]["bodies"].append((citation_id, body))
        source_groups = sorted(grouped.values(), key=lambda item: -int(item["score"]))
        if source_groups:
            minimum_score = max(1, math.ceil(int(source_groups[0]["score"]) * 0.8))
            source_groups = [item for item in source_groups if int(item["score"]) >= minimum_score][
                :2
            ]
        for group in source_groups:
            source_bodies = list(group["bodies"])
            body = "；".join(body for _, body in source_bodies)
            excerpt = body[:220].rstrip()
            if len(body) > len(excerpt):
                excerpt += "…"
            blocks.append(
                {
                    "text": f"根据本站已发布内容：{excerpt}",
                    "citation_ids": [alias for alias, _ in source_bodies],
                    "supports": [{"citation_id": alias, "quote": raw_quotes[alias]}
                                 for alias, _ in source_bodies],
                }
            )
        if not blocks:
            blocks.append(
                {
                    "text": "当前已发布语料中没有足够信息回答这个问题。",
                    "citation_ids": [],
                }
            )
        return ScriptedChatTurn(parsed={"blocks": blocks})


def build_chat_model(settings: Settings) -> BaseChatModel:
    provider = settings.assistant_chat_provider
    if provider == PROVIDER_TEST:
        if settings.environment == "production":
            raise RuntimeError("test chat provider is not allowed in production")
        if settings.assistant_local_dev_mode:
            return DevelopmentEvidenceChatModel()
        return DeterministicChatModel()
    if provider != PROVIDER_OPENAI_COMPATIBLE:
        raise RuntimeError(f"unsupported chat provider {provider!r}")
    model = settings.assistant_chat_model
    api_key = settings.assistant_chat_api_key
    if model is None or api_key is None:
        raise RuntimeError("chat provider configuration is incomplete")
    deepseek_endpoint = (
        (settings.assistant_chat_endpoint or "").rstrip("/")
        in {"https://api.deepseek.com", "https://api.deepseek.com/v1"}
    )
    explicit_deepseek = settings.assistant_chat_output_protocol == "deepseek-json-object"
    if explicit_deepseek and not deepseek_endpoint:
        raise RuntimeError("DeepSeek JSON protocol requires the official HTTPS endpoint")
    if settings.environment == "production" and deepseek_endpoint and not explicit_deepseek:
        raise RuntimeError("production DeepSeek requires an explicit JSON output contract")
    local_deepseek = deepseek_endpoint and (
        settings.environment == "development" or explicit_deepseek
    )
    if local_deepseek and not settings.assistant_chat_max_output_tokens:
        raise RuntimeError("local DeepSeek requires an explicit output token limit")
    chat_type = LocalDeepSeekChatOpenAI if local_deepseek else ChatOpenAI
    token_options: dict[str, Any] = {}
    if local_deepseek and model == "deepseek-flash":
        from .deepseek_tokenizer import token_ids

        if settings.environment == "production":
            # Fail before readiness/admission; never make the first visitor fetch assets.
            token_ids("")
        token_options["custom_get_token_ids"] = token_ids
    return chat_type(
        model=model,
        api_key=SecretStr(api_key),
        base_url=settings.assistant_chat_endpoint,
        use_responses_api=False,
        streaming=False,
        disable_streaming=True,
        max_retries=0,
        timeout=settings.assistant_provider_timeout_seconds,
        max_completion_tokens=settings.assistant_chat_max_output_tokens,
        **token_options,
    )


def build_metered_embeddings(settings: Settings) -> MeteredEmbeddings:
    provider = settings.assistant_embedding_provider
    dimension = settings.assistant_embedding_dimension or 32
    if provider == PROVIDER_TEST:
        if settings.environment == "production":
            raise RuntimeError("test embedding provider is not allowed in production")
        embedding_type = (
            DevelopmentLexicalEmbeddings
            if settings.assistant_local_dev_mode
            else DeterministicHashEmbeddings
        )
        inner = embedding_type(
            dimension=dimension,
            model=settings.assistant_embedding_model or TEST_EMBEDDING_MODEL,
            version=settings.assistant_embedding_model_version or TEST_EMBEDDING_MODEL_VERSION,
        )
        return DeterministicMeteredEmbeddings(inner)
    if provider != PROVIDER_OPENAI_COMPATIBLE:
        raise RuntimeError(f"unsupported embedding provider {provider!r}")
    timeout = float(settings.assistant_provider_timeout_seconds or 30)
    adapter: Callable[..., MeteredEmbeddings] = OpenAICompatibleMeteredEmbeddings
    extra: dict[str, Any] = {}
    from ..local_embedding.artifact import MODEL

    if settings.assistant_embedding_model == MODEL:
        from ..local_embedding.client import E5Embeddings, validate_e5_settings

        validate_e5_settings(settings)
        adapter = E5Embeddings
        extra["model_directory"] = settings.assistant_e5_model_dir
        extra["ca_file"] = settings.assistant_e5_ca_file
    return adapter(
        model=str(settings.assistant_embedding_model),
        version=str(settings.assistant_embedding_model_version),
        api_key=str(settings.assistant_embedding_api_key),
        base_url=str(settings.assistant_embedding_endpoint),
        dimension=dimension,
        timeout=timeout,
        max_batch_items=int(settings.assistant_embedding_max_batch_items or 1),
        **extra,
    )


def credential_fingerprint(secret: str, value: str, label: str) -> str:
    digest = hashlib.sha256(f"{label}|{value}".encode()).digest()
    import hmac

    return hmac.new(secret.encode("utf-8"), digest, hashlib.sha256).hexdigest()
