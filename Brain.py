import google.generativeai as genai
import logging
import time
from typing import Optional, Any

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_DELAY = 1.0


def generate_response(
    api_key: str,
    model_name: str,
    prompt: str,
    system_instruction: Optional[str] = None,
    file_path: Optional[str] = None,
    conversation_history: Optional[list[dict[str, Any]]] = None,
    max_retries: int = MAX_RETRIES
) -> str:
    last_error = None

    for attempt in range(max_retries):
        try:
            genai.configure(api_key=api_key)

            model = genai.GenerativeModel(
                model_name,
                system_instruction=system_instruction
            )

            chat_history = conversation_history or []

            user_prompt_parts: list[Any] = []
            uploaded_file: Optional[Any] = None

            if file_path:
                try:
                    uploaded_file = genai.upload_file(path=file_path)
                    user_prompt_parts.append(uploaded_file)
                except Exception as e:
                    logger.error("Failed to upload file %s: %s", file_path, e)
                    return f"Failed to upload file: {e}"

            user_prompt_parts.append(prompt)

            content_to_send = chat_history + [{'role': 'user', 'parts': user_prompt_parts}]

            response = model.generate_content(content_to_send)

            if uploaded_file:
                try:
                    genai.delete_file(uploaded_file.name)
                except Exception as e:
                    logger.warning("Failed to delete uploaded file: %s", e)

            return response.text

        except Exception as e:
            last_error = e
            logger.warning("Gemini API attempt %d/%d failed: %s", attempt + 1, max_retries, e)

            if attempt < max_retries - 1:
                delay = BASE_DELAY * (2 ** attempt)
                logger.info("Retrying in %.1f seconds...", delay)
                time.sleep(delay)

    logger.error("All %d retry attempts failed. Last error: %s", max_retries, last_error)
    return f"AI service temporarily unavailable. Please try again later."