import time

from openai import OpenAI, OpenAIError


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

    def chat(self, messages: list[dict]) -> str:
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model, messages=messages, temperature=0.7
                )
                content = response.choices[0].message.content
                if content:
                    return content
                print(f"Empty LLM response (attempt {attempt}/{self.max_retries})")
            except OpenAIError as e:
                print(f"API error (attempt {attempt}/{self.max_retries}): {e}")

            if attempt < self.max_retries:
                time.sleep(self.retry_delay)

        return ""