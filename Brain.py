from google import genai
from google.genai import types
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
            client = genai.Client(api_key=api_key)

            config = types.GenerateContentConfig(
                system_instruction=system_instruction
            )

            # Map old chat history format to the new API if needed
            # For simplicity, assuming the history follows the new structure (role, parts)
            # or converting it here.
            contents = []
            if conversation_history:
                for entry in conversation_history:
                    contents.append(types.Content(role=entry['role'], parts=[types.Part.from_text(text=p) if isinstance(p, str) else p for p in entry['parts']]))

            user_parts = []
            if file_path:
                try:
                    # Upload file using the new API
                    with open(file_path, "rb") as f:
                        file_data = f.read()
                        # For simple images/PDFs, we can send them directly or upload.
                        # The new SDK supports direct upload or using the files service.
                        # Here we'll use a simple approach for the common case.
                        # Note: In production, you might want to handle mime_type specifically.
                        import mimetypes
                        mime_type, _ = mimetypes.guess_type(file_path)
                        user_parts.append(types.Part.from_bytes(data=file_data, mime_type=mime_type or "application/octet-stream"))
                except Exception as e:
                    logger.error("Failed to read file %s: %s", file_path, e)
                    return f"Failed to read file: {e}"

            user_parts.append(types.Part.from_text(text=prompt))
            contents.append(types.Content(role="user", parts=user_parts))

            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )

            return response.text

        except Exception as e:
            last_error = e
            logger.warning("Gemini API attempt %d/%d failed: %s", attempt + 1, max_retries, e)

            if attempt < max_retries - 1:
                delay = BASE_DELAY * (2 ** attempt)
                logger.info("Retrying in %.1f seconds...", delay)
                time.sleep(delay)

    logger.error("All %d retry attempts failed. Last error: %s", max_retries, last_error)
    return "AI service temporarily unavailable\\. Please try again later\\."