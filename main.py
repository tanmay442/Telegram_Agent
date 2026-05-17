from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config import TELEGRAM_BOT_TOKEN, ensure_runtime_dirs, setup_logging
from handlers import (
    cancel_command,
    compress_image_command,
    compress_pdf_command,
    handle_media,
    handle_message,
    hbtu_updates_command,
    help_command,
    start,
    to_images_command,
    to_pdf_command,
)


def build_application() -> Application:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not configured")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler(["hbtu_updates", "hu"], hbtu_updates_command))
    app.add_handler(CommandHandler(["compress_image", "ci"], compress_image_command))
    app.add_handler(CommandHandler(["compress_pdf", "cpdf"], compress_pdf_command))
    app.add_handler(CommandHandler(["to_pdf", "tp"], to_pdf_command))
    app.add_handler(CommandHandler(["to_images", "ti"], to_images_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler((filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND, handle_media))
    return app


def main() -> None:
    setup_logging()
    ensure_runtime_dirs()
    app = build_application()
    app.run_polling()


if __name__ == "__main__":
    main()
