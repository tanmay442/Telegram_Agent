import os

import dotenv

from ai.openrouter_client import generate_response

dotenv.load_dotenv()

api_key = os.environ.get("OPENROUTER_API_KEY", "")
model_name = os.environ.get("MODEL_NAME", "openai/gpt-4.1-mini")

if not api_key:
    raise RuntimeError("OPENROUTER_API_KEY is not set")

response = generate_response(
    api_key=api_key,
    model_name=model_name,
    prompt="Reply with: OpenRouter connection OK",
)
print(response)
