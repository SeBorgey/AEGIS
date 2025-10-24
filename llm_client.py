import re

from openai import OpenAI, OpenAIError


class LLMClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key is not provided.")

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )

    def generate_code(self, messages: list[dict]) -> str:
        try:
            response = self.client.chat.completions.create(
                model="gemini-2.5-pro",
                messages=messages,
                temperature=1,
            )

            content = response.choices[0].message.content

            match = re.search(r"```python\n(.*?)```", content, re.DOTALL)
            if match:
                return match.group(1).strip()
            return content.strip()

        except OpenAIError as e:
            print(f"Ошибка API запроса: {e}")
            return ""
