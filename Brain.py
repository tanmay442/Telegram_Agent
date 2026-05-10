import google.generativeai as genai
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


def generate_response(
    api_key: str,
    model_name: str,
    prompt: str,
    system_instruction: Optional[str] = None,
    file_path: Optional[str] = None,
    conversation_history: Optional[list[dict[str, Any]]] = None
) -> str:
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

        try:
            response = model.generate_content(content_to_send)
        except Exception as e:
            logger.error("Gemini API error: %s", e)
            return f"AI error: {e}"

        if uploaded_file:
            try:
                genai.delete_file(uploaded_file.name)
            except Exception as e:
                logger.warning("Failed to delete uploaded file: %s", e)

        return response.text

    except Exception as e:
        logger.error("Unexpected error in generate_response: %s", e)
        return f"An error occurred: {e}"