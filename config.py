import logging
import os

import dotenv

dotenv.load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.environ.get("MODEL_NAME", "openai/gpt-4.1-mini")
OPENROUTER_REFERER = os.environ.get("OPENROUTER_REFERER", "")
OPENROUTER_APP_NAME = os.environ.get("OPENROUTER_APP_NAME", "Telegram Agent")

OUTPUT_DIR = "Temp/Output"
MAX_TELEGRAM_MSG_LEN = 4096

HELP_TEXT = """
*Available Commands:*

*AI Chat*
Send any message and I'll respond with AI assistance.

*File Operations*
`/compress_image` `/ci` - Compress an image
`/compress_pdf` `/cpdf` - Compress a PDF
`/to_pdf` `/tp` - Convert image to PDF
`/to_images` `/ti` - Convert PDF to images

*Utility*
`/hbtu_updates` `/hu` - Check HBTU circulars
`/cancel` - Cancel current operation
`/help` - Show this help message

*Rate Limits*
AI: 5 requests per minute (warning at 3)
File ops: 100 per hour
""".strip()


def setup_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )


def ensure_runtime_dirs() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs("Temp", exist_ok=True)
