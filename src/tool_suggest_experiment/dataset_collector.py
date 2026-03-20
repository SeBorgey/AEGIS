import asyncio
from tool_suggest.client import ToolSuggestClient
from tool_suggest_experiment.message_converter import openai_messages_to_pydantic


class AegisDatasetCollector:
    def __init__(self, client: ToolSuggestClient):
        self.client = client

    def record_step(self, messages: list[dict], selected_tool: str):
        context = openai_messages_to_pydantic(messages)
        asyncio.get_event_loop().run_until_complete(
            self.client.record(context=context, selected_tools=[selected_tool])
        )

    async def record_step_async(self, messages: list[dict], selected_tool: str):
        context = openai_messages_to_pydantic(messages)
        await self.client.record(context=context, selected_tools=[selected_tool])
