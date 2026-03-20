from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    UserPromptPart,
    TextPart,
)


def openai_messages_to_pydantic(messages: list[dict]) -> list[ModelMessage]:
    result: list[ModelMessage] = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                part.get("text", "") for part in content if isinstance(part, dict) and part.get("type") == "text"
            )
        if role == "system":
            result.append(ModelRequest(parts=[SystemPromptPart(content=content)]))
        elif role == "user":
            result.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif role == "assistant":
            result.append(ModelResponse(parts=[TextPart(content=content)]))
    return result
