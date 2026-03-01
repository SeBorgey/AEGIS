import time

from openai import OpenAI, OpenAIError
from pydantic import BaseModel
from typing import Type, Optional, Union

class LLMClient:
    def __init__(self, api_key: str, model: str = "gemini-3-flash-preview", max_retries: int = 3, retry_delay: float = 5.0):
        if not api_key:
            raise ValueError("API key required")

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def chat(self, messages: list[dict], response_model: Optional[Type[BaseModel]] = None) -> Union[str, BaseModel, None]:
        for attempt in range(1, self.max_retries + 1):
            try:
                if response_model:
                    schema = response_model.model_json_schema()
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        response_format={
                            "type": "json_schema",
                            "json_schema": {
                                "name": response_model.__name__,
                                "schema": schema
                            }
                        }
                    )
                    content = response.choices[0].message.content
                    if content:
                        import re
                        clean_content = re.sub(r"^```json\s*|\s*```$", "", content.strip())
                        return response_model.model_validate_json(clean_content)
                else:
                    response = self.client.chat.completions.create(
                        model=self.model, messages=messages, temperature=0.7
                    )
                    content = response.choices[0].message.content
                    if content:
                        return content
                print(f"Empty LLM response (attempt {attempt}/{self.max_retries})")
            except Exception as e:
                print(f"API error (attempt {attempt}/{self.max_retries}): {e}")

            if attempt < self.max_retries:
                time.sleep(self.retry_delay)

        return None if response_model else ""