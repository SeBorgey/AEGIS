from unittest.mock import MagicMock, AsyncMock, patch
from tool_suggest_experiment.dataset_collector import AegisDatasetCollector


def test_record_step_calls_client():
    mock_client = MagicMock()
    mock_client.record = AsyncMock()
    collector = AegisDatasetCollector(mock_client)

    messages = [
        {"role": "system", "content": "You are an agent."},
        {"role": "user", "content": "Task: test"},
    ]

    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        collector.record_step(messages, "read_file")
        assert mock_client.record.await_count == 1
        call_args = mock_client.record.call_args
        assert call_args.kwargs["selected_tools"] == ["read_file"]
        context = call_args.kwargs["context"]
        assert len(context) == 2
    finally:
        loop.close()


def test_record_step_async():
    mock_client = MagicMock()
    mock_client.record = AsyncMock()
    collector = AegisDatasetCollector(mock_client)

    messages = [{"role": "user", "content": "Hello"}]

    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(collector.record_step_async(messages, "create_file"))
        assert mock_client.record.await_count == 1
    finally:
        loop.close()
