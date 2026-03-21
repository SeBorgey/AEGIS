from pydantic_ai.messages import ModelRequest, ModelResponse, SystemPromptPart, UserPromptPart, TextPart

from tool_suggest_experiment.message_converter import openai_messages_to_pydantic


def test_system_message():
    msgs = [{"role": "system", "content": "You are an agent."}]
    result = openai_messages_to_pydantic(msgs)
    assert len(result) == 1
    assert isinstance(result[0], ModelRequest)
    assert isinstance(result[0].parts[0], SystemPromptPart)
    assert result[0].parts[0].content == "You are an agent."


def test_user_message():
    msgs = [{"role": "user", "content": "Hello!"}]
    result = openai_messages_to_pydantic(msgs)
    assert len(result) == 1
    assert isinstance(result[0], ModelRequest)
    assert isinstance(result[0].parts[0], UserPromptPart)
    assert result[0].parts[0].content == "Hello!"


def test_assistant_message():
    msgs = [{"role": "assistant", "content": "I will help you."}]
    result = openai_messages_to_pydantic(msgs)
    assert len(result) == 1
    assert isinstance(result[0], ModelResponse)
    assert isinstance(result[0].parts[0], TextPart)
    assert result[0].parts[0].content == "I will help you."


def test_empty_list():
    result = openai_messages_to_pydantic([])
    assert result == []


def test_full_conversation():
    msgs = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Task: test"},
        {"role": "assistant", "content": "Thinking..."},
        {"role": "user", "content": "Result: ok"},
    ]
    result = openai_messages_to_pydantic(msgs)
    assert len(result) == 4
    assert isinstance(result[0], ModelRequest)
    assert isinstance(result[1], ModelRequest)
    assert isinstance(result[2], ModelResponse)
    assert isinstance(result[3], ModelRequest)


def test_multipart_content():
    msgs = [{"role": "user", "content": [
        {"type": "text", "text": "Hello "},
        {"type": "text", "text": "world"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
    ]}]
    result = openai_messages_to_pydantic(msgs)
    assert len(result) == 1
    assert isinstance(result[0], ModelRequest)
    assert result[0].parts[0].content == "Hello  world"
