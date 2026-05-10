import os
import logging
import shutil
import asyncio
import signal
import sys
import dotenv
import traceback
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

from FileActions.img_compress import compress_image
from FileActions.pdf_compress import compress_pdf
from FileActions.img_pdf import convert_image_to_pdf, convert_pdf_to_images
from hbtu_updates.cheking_update import check_for_updates
from media_extractor import extract_file
from Brain import generate_response

dotenv.load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = os.environ.get("MODEL_NAME")

OUTPUT_DIR = "Temp/Output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

user_histories: dict[int, list] = {}
user_actions: dict[int, str] = {}
MAX_HISTORY_LENGTH = 10

shutdown_event = asyncio.Event()


def escape_markdown_v2(text: str) -> str:
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_text = (
        "Hi! I'm ready to assist you.\n\n"
        "You can send me a photo of a question and I can provide solutions.\n\n"
        "*Available Commands:*\n"
        "/hbtu_updates - Check for new HBTU circulars\n"
        "/compress_image - Compress an image\n"
        "/compress_pdf - Compress a PDF\n"
        "/to_pdf - Convert image to PDF\n"
        "/to_images - Convert PDF to images\n"
        "/cancel - Cancel current operation"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN_V2)


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id in user_actions:
        del user_actions[user_id]
        logger.info("User %s canceled their action.", user_id)
        await update.message.reply_text("Your current action has been canceled.")
    else:
        await update.message.reply_text("You have no active action to cancel.")


async def hbtu_updates_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    await update.message.reply_text("Checking for the latest HBTU updates, this may take a moment...")
    logger.info("User %s initiated HBTU update check.", user_id)

    try:
        new_updates = await asyncio.to_thread(check_for_updates)
        if not new_updates:
            await update.message.reply_text("No new updates found on the HBTU website.")
            return

        logger.info("Found %d updates.", len(new_updates))

        system_prompt = (
            "Format the following university updates for a Telegram message. "
            "Use Telegram MarkdownV2 formatting. "
            "Present updates in a human-readable way with bold titles and links.\n"
            "Source: Exam | Academic | Conference"
        )

        prompt = f"Data: {new_updates}"
        formatted_response = generate_response(
            api_key=GEMINI_API_KEY,
            model_name=MODEL_NAME,
            prompt=prompt,
            system_instruction=system_prompt
        )
        await update.message.reply_text(formatted_response, parse_mode=ParseMode.MARKDOWN_V2)

    except Exception:
        error_details = traceback.format_exc()
        logger.error("HBTU update error: %s\n%s", update, error_details)
        await update.message.reply_text("An error occurred while checking updates. Please try again later.")


async def file_action_command(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, message: str):
    user_id = update.message.from_user.id
    user_actions[user_id] = action
    logger.info("User %s initiated action: %s", user_id, action)
    await update.message.reply_text(message)


async def compress_image_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await file_action_command(update, context, 'compress_image', 'Please send the image you want to compress.')


async def compress_pdf_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await file_action_command(update, context, 'compress_pdf', 'Please send the PDF you want to compress.')


async def to_pdf_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await file_action_command(update, context, 'to_pdf', 'Please send the image to convert to PDF.')


async def to_images_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await file_action_command(update, context, 'to_images', 'Please send the PDF to convert into images.')


def get_user_history(user_id: int) -> list:
    return user_histories.setdefault(user_id, [])


def add_to_history(user_id: int, role: str, text: str):
    history = get_user_history(user_id)
    history.append({'role': role, 'parts': [text]})
    if len(history) > MAX_HISTORY_LENGTH:
        user_histories[user_id] = history[-MAX_HISTORY_LENGTH:]


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    text = update.message.text
    add_to_history(user_id, "user", text)

    try:
        response_text = generate_response(
            api_key=GEMINI_API_KEY,
            model_name=MODEL_NAME,
            prompt=text,
            conversation_history=get_user_history(user_id)
        )
    except Exception as e:
        logger.error("Brain error for user %s: %s", user_id, e)
        response_text = "Sorry, I encountered an error. Please try again."

    add_to_history(user_id, "model", response_text)
    await update.message.reply_text(response_text)


async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    action = user_actions.get(user_id)
    if action:
        await process_file_action(update, context, action)
    else:
        await analyze_file_with_brain(update, context)


async def process_file_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
    user_id = update.message.from_user.id

    action_requirements = {
        'compress_image': {'type': 'photo', 'message': 'Please send an image file for this action.'},
        'to_pdf': {'type': 'photo', 'message': 'Please send an image file for this action.'},
        'compress_pdf': {'type': 'document', 'mime': 'application/pdf', 'message': 'Please send a PDF document.'},
        'to_images': {'type': 'document', 'mime': 'application/pdf', 'message': 'Please send a PDF document.'},
    }
    req = action_requirements[action]

    valid_file = False
    file_id = None

    if req['type'] == 'photo' and update.message.photo:
        valid_file = True
        file_id = update.message.photo[-1].file_id
    elif req['type'] == 'document' and update.message.document and update.message.document.mime_type == req['mime']:
        valid_file = True
        file_id = update.message.document.file_id

    if not valid_file:
        await update.message.reply_text(req['message'] + "\nOr type /cancel to stop.")
        return

    del user_actions[user_id]
    await update.message.reply_text(f"File received. Starting '{action}'...")

    input_path = None
    output_path = None

    try:
        input_path = await extract_file(context.bot, file_id)
        if not input_path:
            raise ValueError("File could not be downloaded from Telegram.")

        action_funcs = {
            'compress_image': compress_image,
            'compress_pdf': compress_pdf,
            'to_pdf': convert_image_to_pdf,
            'to_images': convert_pdf_to_images
        }
        output_path = action_funcs[action](input_path, OUTPUT_DIR)

        if output_path and os.path.exists(output_path):
            if os.path.isdir(output_path):
                await update.message.reply_text("Action complete. Sending your files...")
                for filename in sorted(os.listdir(output_path)):
                    filepath = os.path.join(output_path, filename)
                    with open(filepath, 'rb') as f:
                        await context.bot.send_document(chat_id=user_id, document=f)
            else:
                await update.message.reply_text("Action complete. Sending your file...")
                with open(output_path, 'rb') as f:
                    await context.bot.send_document(chat_id=user_id, document=f)
        else:
            await update.message.reply_text("The action failed or no changes were made.")

    except Exception as e:
        logger.error("File action '%s' error for user %s: %s", action, user_id, e)
        await update.message.reply_text(f"An error occurred: {e}")

    finally:
        if input_path and os.path.exists(input_path):
            try:
                os.remove(input_path)
            except OSError:
                pass
        if output_path and output_path != input_path and os.path.exists(output_path):
            if os.path.isdir(output_path):
                shutil.rmtree(output_path, ignore_errors=True)
            else:
                try:
                    os.remove(output_path)
                except OSError:
                    pass


async def analyze_file_with_brain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = None
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document:
        file_id = update.message.document.file_id

    if not file_id:
        return await update.message.reply_text("File type not suitable for analysis.")

    await update.message.reply_text('File received, analyzing with AI...')
    file_path = None

    try:
        file_path = await extract_file(context.bot, file_id)
        if not file_path:
            await update.message.reply_text("Failed to download file. Please try again.")
            return

        prompt = update.message.caption or "Describe this file in detail. If there are questions, solve them with detailed answers."
        response_text = generate_response(
            api_key=GEMINI_API_KEY,
            model_name=MODEL_NAME,
            prompt=prompt,
            file_path=file_path,
            conversation_history=get_user_history(update.message.from_user.id)
        )

        MAX_MSG_LEN = 4096
        if len(response_text) > MAX_MSG_LEN:
            for i in range(0, len(response_text), MAX_MSG_LEN):
                await update.message.reply_text(response_text[i:i+MAX_MSG_LEN])
        else:
            await update.message.reply_text(response_text)

        add_to_history(update.message.from_user.id, "model", response_text)

    except Exception as e:
        logger.error("Brain analysis error: %s", e)
        await update.message.reply_text("An error occurred while analyzing the file.")

    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass


async def shutdown_signal_handler(app: Application, signal_received: int, loop: asyncio.AbstractEventLoop):
    logger.info("Shutdown signal received (signal %d). Stopping bot...", signal_received)
    shutdown_event.set()
    await app.stop()


def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CommandHandler("hbtu_updates", hbtu_updates_command))
    application.add_handler(CommandHandler("compress_image", compress_image_command))
    application.add_handler(CommandHandler("compress_pdf", compress_pdf_command))
    application.add_handler(CommandHandler("to_pdf", to_pdf_command))
    application.add_handler(CommandHandler("to_images", to_images_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler((filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND, handle_media))

    loop = asyncio.get_event_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown_signal_handler(application, s, loop)))

    logger.info("Bot is starting...")
    application.run_polling(stop_event=shutdown_event)


if __name__ == '__main__':
    main()