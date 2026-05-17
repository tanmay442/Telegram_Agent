from typing import Any

from ai.openrouter_client import generate_response

SYSTEM_PROMPT = (
    "You format HBTU updates for Telegram in plain text. Keep the message concise and scannable. "
    "For each update include source, title and URL on separate lines. Do not use markdown syntax."
)


def _fallback_format(updates: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for item in updates:
        source = item.get("source", "Unknown")
        text = item.get("text", "Untitled")
        link = item.get("link", "")
        lines.append(f"{source}\n{text}\n{link}")
    return "\n\n".join(lines) if lines else "No updates found."


def format_hbtu_updates(updates: list[dict[str, Any]], api_key: str, model_name: str) -> str:
    if not updates:
        return "No new updates found on the HBTU website."
    if not api_key:
        return _fallback_format(updates)

    prompt = f"Format this update list for Telegram:\n{updates}"
    try:
        return generate_response(
            api_key=api_key,
            model_name=model_name,
            prompt=prompt,
            system_instruction=SYSTEM_PROMPT,
        )
    except Exception:
        return _fallback_format(updates)
