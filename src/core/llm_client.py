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
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    def _accumulate_usage(self, response):
        usage = getattr(response, "usage", None)
        if usage:
            self.total_prompt_tokens += getattr(usage, "prompt_tokens", 0) or 0
            self.total_completion_tokens += getattr(usage, "completion_tokens", 0) or 0

    def get_token_usage(self) -> dict:
        return {
            "prompt": self.total_prompt_tokens,
            "completion": self.total_completion_tokens,
            "total": self.total_prompt_tokens + self.total_completion_tokens,
        }

    def reset_token_usage(self):
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    def chat(self, messages: list[dict], response_model: Optional[Type[BaseModel]] = None) -> Union[str, BaseModel, None]:
        for attempt in range(1, self.max_retries + 1):
            try:
                if response_model:
                    response = self.client.chat.completions.parse(
                        model=self.model,
                        messages=messages,
                        response_format=response_model,
                    )
                    self._accumulate_usage(response)
                    message = response.choices[0].message
                    if getattr(message, "parsed", None):
                        return message.parsed
                    elif getattr(message, "refusal", None):
                        print(f"Model refused: {message.refusal}")
                else:
                    response = self.client.chat.completions.create(
                        model=self.model, messages=messages, temperature=0.7
                    )
                    self._accumulate_usage(response)
                    content = response.choices[0].message.content
                    if content:
                        return content
                print(f"Empty LLM response (attempt {attempt}/{self.max_retries})")
            except Exception as e:
                print(f"API error (attempt {attempt}/{self.max_retries}): {e}")

            if attempt < self.max_retries:
                time.sleep(self.retry_delay)

        return None if response_model else ""