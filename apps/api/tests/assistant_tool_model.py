"""Native-tool test double for the catalog's metered runtime path."""

from __future__ import annotations

import asyncio
from contextlib import contextmanager

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from app.assistant.constants import TEST_CHAT_MODEL, TEST_CHAT_MODEL_VERSION
from app.assistant.providers import DeterministicChatModel

from .test_assistant_online import _online_client


class ArticleToolChatModel(DeterministicChatModel):
    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        assert tool_choice == "auto"
        assert tools[0]["function"]["name"] == "list_recent_articles"

        def reply(messages):
            scripted = bool(self.script)
            turn = self._next(list(messages))
            if scripted:
                calls = turn.parsed.get("tool_calls", [])
            else:
                question = str(messages[-1][1])
                calls = (
                    []
                    if "草稿" in question
                    else [
                        {
                            "name": "list_recent_articles",
                            "id": "catalog-test-call",
                            "args": {"order": "updated", "limit": 5, "window": None},
                        }
                    ]
                )
            return AIMessage(
                content="",
                tool_calls=calls,
                response_metadata={
                    "finish_reason": turn.finish_reason
                    if scripted
                    else ("tool_calls" if calls else "stop"),
                    "model_name": TEST_CHAT_MODEL,
                    "model_version": TEST_CHAT_MODEL_VERSION,
                },
                usage_metadata={
                    "input_tokens": turn.input_tokens,
                    "output_tokens": turn.output_tokens,
                    "total_tokens": turn.input_tokens + turn.output_tokens,
                },
            )

        async def areply(messages):
            if self._hold is not None:
                self._hold_loop = asyncio.get_running_loop()
                self._started.set()
                await self._hold.wait()
            return reply(messages)

        return RunnableLambda(reply, afunc=areply)


@contextmanager
def tool_online_client(*args, **kwargs):
    with _online_client(*args, **kwargs) as client:
        client.app.state.assistant.chat = ArticleToolChatModel()
        yield client
