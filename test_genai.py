from google import genai
from google.genai import types
import os
import dotenv

dotenv.load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)
print("Client created")

try:
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite", 
        contents="Hello"
    )
    print("Response:", response.text)
except Exception as e:
    print("Error:", repr(e))
