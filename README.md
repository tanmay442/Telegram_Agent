# Telegram Agent

Telegram bot for:
- AI chat and file analysis (OpenRouter)
- File utilities (image/pdf compression + conversion)
- HBTU updates with cached scraping and new-link tracking

## Architecture

- `main.py`: startup pipeline only (build app, register handlers, run polling)
- `handlers/`: Telegram command/message handlers
- `services/`: file pipeline and HBTU response formatting
- `ai/openrouter_client.py`: OpenRouter chat + multimodal/file context handling
- `hbtu_updates/`: scraping + temporary SQLite cache (`Temp/hbtu_cache.db`)
- `FileActions/`: image/pdf processing utilities
- `session_manager.py`: user sessions + request/file-operation rate limits

## Environment

Create a `.env` file with:

```env
TELEGRAM_BOT_TOKEN=...
OPENROUTER_API_KEY=...
MODEL_NAME=openai/gpt-4.1-mini
OPENROUTER_REFERER=
OPENROUTER_APP_NAME=Telegram Agent
```

## Setup

1. `python3 -m pip install -r requirements.txt`
2. Configure `.env`
3. `python3 main.py`

## Notes

- Google services and related auth flows are removed.
- HBTU requests are cached for 30 minutes in a temporary SQLite DB to reduce repeated scraping.
