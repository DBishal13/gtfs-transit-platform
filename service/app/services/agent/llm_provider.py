"""Provider-agnostic LLM abstraction. orchestrator.py and tools.py depend only on the
LLMProvider Protocol and the ToolCall/LLMResponse shapes below — never on either vendor
SDK directly — so swapping providers is a one-line config change (LLM_PROVIDER=anthropic
or LLM_PROVIDER=openai), not a code change.

The canonical, provider-agnostic message format the orchestrator builds and maintains
follows Anthropic's Messages API content-block shape:
    {"role": "user" | "assistant", "content": str | list[dict]}
    content blocks: {"type": "text", "text": ...}
                     {"type": "tool_use", "id": ..., "name": ..., "input": {...}}
                     {"type": "tool_result", "tool_use_id": ..., "content": "..."}
AnthropicProvider passes this through almost unchanged; OpenAIProvider translates it to
and from OpenAI's flat tool_calls/role="tool" message shape internally, so the
orchestrator never has to know which wire format is actually in use.
"""

from __future__ import annotations

import json

from pydantic import BaseModel

from service.app.config import Settings
from service.app.services.agent.tool_schemas import ToolDefinition


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class LLMResponse(BaseModel):
    text: str | None = None
    tool_calls: list[ToolCall] = []
    stop_reason: str
    usage: TokenUsage = TokenUsage()


class LLMProvider:
    """Structural interface (not ABC — kept minimal so a test fake needs no inheritance)."""

    def chat(self, *, messages: list[dict], tools: list[ToolDefinition], system: str) -> LLMResponse:
        raise NotImplementedError


class AnthropicProvider(LLMProvider):
    def __init__(self, *, api_key: str, model: str) -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def chat(self, *, messages: list[dict], tools: list[ToolDefinition], system: str) -> LLMResponse:
        anthropic_tools = [
            {"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in tools
        ]
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            tools=anthropic_tools,
            messages=messages,
        )

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=block.input))

        return LLMResponse(
            text="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            usage=TokenUsage(
                input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens
            ),
        )


def _canonical_messages_to_openai(messages: list[dict]) -> list[dict]:
    converted: list[dict] = []
    for msg in messages:
        role, content = msg["role"], msg["content"]
        if isinstance(content, str):
            converted.append({"role": role, "content": content})
            continue

        if role == "assistant":
            text_parts = [b["text"] for b in content if b.get("type") == "text"]
            tool_use_blocks = [b for b in content if b.get("type") == "tool_use"]
            entry: dict = {"role": "assistant", "content": "\n".join(text_parts) or None}
            if tool_use_blocks:
                entry["tool_calls"] = [
                    {
                        "id": b["id"],
                        "type": "function",
                        "function": {"name": b["name"], "arguments": json.dumps(b["input"])},
                    }
                    for b in tool_use_blocks
                ]
            converted.append(entry)
        else:  # user role carrying tool_result blocks
            for block in content:
                if block.get("type") == "tool_result":
                    converted.append(
                        {"role": "tool", "tool_call_id": block["tool_use_id"], "content": block["content"]}
                    )
    return converted


class OpenAIProvider(LLMProvider):
    def __init__(self, *, api_key: str, model: str) -> None:
        import openai

        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def chat(self, *, messages: list[dict], tools: list[ToolDefinition], system: str) -> LLMResponse:
        openai_messages = [{"role": "system", "content": system}, *_canonical_messages_to_openai(messages)]
        openai_tools = [
            {
                "type": "function",
                "function": {"name": t.name, "description": t.description, "parameters": t.input_schema},
            }
            for t in tools
        ]

        response = self._client.chat.completions.create(
            model=self._model, messages=openai_messages, tools=openai_tools or None
        )
        choice = response.choices[0]
        message = choice.message
        tool_calls = [
            ToolCall(id=tc.id, name=tc.function.name, arguments=json.loads(tc.function.arguments))
            for tc in (message.tool_calls or [])
        ]
        usage = response.usage
        return LLMResponse(
            text=message.content,
            tool_calls=tool_calls,
            stop_reason=choice.finish_reason,
            usage=TokenUsage(
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
            ),
        )


def get_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("LLM_PROVIDER=openai requires OPENAI_API_KEY to be set")
        return OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model)
    if not settings.anthropic_api_key:
        raise RuntimeError("LLM_PROVIDER=anthropic requires ANTHROPIC_API_KEY to be set")
    return AnthropicProvider(api_key=settings.anthropic_api_key, model=settings.anthropic_model)
