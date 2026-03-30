import asyncio
import threading
from tool_suggest.client import ToolSuggestClient
from tool_suggest_experiment.message_converter import openai_messages_to_pydantic

_loop = asyncio.new_event_loop()
def _start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()
threading.Thread(target=_start_loop, args=(_loop,), daemon=True).start()

class AegisDatasetCollector:
    def __init__(self, client: ToolSuggestClient):
        self.client = client

    def record_step(self, messages: list[dict], selected_tool: str):
        context = openai_messages_to_pydantic(messages)
        future = asyncio.run_coroutine_threadsafe(
            self.client.record(context=context, selected_tools=[selected_tool]), _loop
        )
        future.result()

    async def record_step_async(self, messages: list[dict], selected_tool: str):
        context = openai_messages_to_pydantic(messages)
        await self.client.record(context=context, selected_tools=[selected_tool])
