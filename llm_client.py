from openai import OpenAI, OpenAIError


class LLMClient:
    def __init__(self, api_key: str, model: str = "gemini-3-flash-preview"):
        if not api_key:
            raise ValueError("API key required")

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        self.model = model

    def chat(self, messages: list[dict]) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=0.7
            )
            return response.choices[0].message.content
        except OpenAIError as e:
            print(f"API error: {e}")
            return ""