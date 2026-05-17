import base64
import logging
import mimetypes
import time
from typing import Any, Optional

import requests
from pypdf import PdfReader

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_RETRIES = 3
BASE_DELAY_SECONDS = 1.0


def _normalize_history_text(parts: Any) -> str:
    if not isinstance(parts, list):
        return ""
    normalized: list[str] = []
    for part in parts:
        if isinstance(part, str):
            normalized.append(part)
        elif isinstance(part, dict) and isinstance(part.get("text"), str):
            normalized.append(part["text"])
    return "\n".join(chunk for chunk in normalized if chunk).strip()


def _conversation_to_messages(history: Optional[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    if not history:
        return []

    messages: list[dict[str, Any]] = []
    for entry in history:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role", "user")
        if role == "model":
            role = "assistant"
        if role not in {"user", "assistant", "system"}:
            role = "user"
        text = _normalize_history_text(entry.get("parts", []))
        if text:
            messages.append({"role": role, "content": text})
    return messages


def _extract_pdf_text(file_path: str, max_pages: int = 3, max_chars: int = 6000) -> str:
    reader = PdfReader(file_path)
    chunks: list[str] = []
    for page in reader.pages[:max_pages]:
        page_text = page.extract_text() or ""
        if page_text.strip():
            chunks.append(page_text.strip())
        if sum(len(chunk) for chunk in chunks) >= max_chars:
            break
    text = "\n\n".join(chunks).strip()
    return text[:max_chars]


def _file_content_parts(file_path: str) -> list[dict[str, Any]]:
    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or "application/octet-stream"

    if mime_type.startswith("image/"):
        with open(file_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        data_url = f"data:{mime_type};base64,{encoded}"
        return [{"type": "image_url", "image_url": {"url": data_url}}]

    if mime_type == "application/pdf":
        extracted = _extract_pdf_text(file_path)
        if not extracted:
            return [{"type": "text", "text": "No readable text was extracted from the PDF."}]
        return [{"type": "text", "text": f"Extracted PDF content:\n{extracted}"}]

    if mime_type.startswith("text/"):
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(6000)
        return [{"type": "text", "text": f"Attached file content:\n{content}"}]

    return [{"type": "text", "text": f"Attached file type `{mime_type}` cannot be directly parsed."}]


def _extract_response_text(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("OpenRouter response missing choices")

    message = choices[0].get("message", {})
    content = message.get("content")

    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts).strip()

    raise ValueError("OpenRouter response content is empty")


def generate_response(
    api_key: str,
    model_name: str,
    prompt: str,
    system_instruction: Optional[str] = None,
    file_path: Optional[str] = None,
    conversation_history: Optional[list[dict[str, Any]]] = None,
    referer: str = "",
    app_name: str = "Telegram Agent",
    max_retries: int = MAX_RETRIES,
) -> str:
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured")

    messages: list[dict[str, Any]] = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.extend(_conversation_to_messages(conversation_history))

    user_content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    if file_path:
        user_content.extend(_file_content_parts(file_path))

    messages.append({"role": "user", "content": user_content})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if referer:
        headers["HTTP-Referer"] = referer
    if app_name:
        headers["X-Title"] = app_name

    payload = {
        "model": model_name,
        "messages": messages,
    }

    last_error: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=90,
            )
            response.raise_for_status()
            body = response.json()
            text = _extract_response_text(body)
            if not text:
                raise ValueError("OpenRouter returned empty text")
            return text
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            logger.warning(
                "OpenRouter attempt %d/%d failed: %s",
                attempt + 1,
                max_retries,
                exc,
            )
            if attempt < max_retries - 1:
                time.sleep(BASE_DELAY_SECONDS * (2**attempt))

    raise RuntimeError(f"OpenRouter request failed after {max_retries} attempts: {last_error}")
