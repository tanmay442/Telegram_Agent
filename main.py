import os
import logging
import shutil
import asyncio
import signal
import dotenv
import traceback
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

from FileActions.img_compress import compress_image
from FileActions.pdf_compress import compress_pdf
from FileActions.img_pdf import convert_image_to_pdf, convert_pdf_to_images
from hbtu_updates.cheking_update import check_for_updates
from media_extractor import extract_file
from Brain import generate_response
from session_manager import SessionManager, ActionState

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

shutdown_event = asyncio.Event()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sm = SessionManager()
    user_id = update.message.from_user.id

    ai_quota = sm.get_ai_quota(user_id)

    welcome_text = (
        "Hi! I'm ready to assist you.\n\n"
        "You can send me a photo of a question and I can provide solutions.\n\n"
        "*Available Commands:*\n"
        "/hbtu_updates - Check for new HBTU circulars\n"
        "/compress_image - Compress an image\n"
        "/compress_pdf - Compress a PDF\n"
        "/to_pdf - Convert image to PDF\n"
        "/to_images - Convert PDF to images\n"
        "/cancel - Cancel current operation\n\n"
        f"_{ai_quota}_"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN_V2)


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    sm = SessionManager()
    if sm.get_session(user_id).action_state != ActionState.NONE:
        sm.clear_action(user_id)
        logger.info("User %s canceled their action.", user_id)
        await update.message.reply_text("Your current action has been canceled.")
    else:
        await update.message.reply_text("You have no active action to cancel.")


async def hbtu_updates_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    sm = SessionManager()

    allowed, message = sm.check_ai_rate_limit(user_id)
    if not allowed:
        await update.message.reply_text(message)
        return

    await update.message.reply_text("Checking for the latest HBTU updates, this may take a moment...")
    logger.info("User %s initiated HBTU update check.", user_id)

    sm.record_ai_request(user_id)

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
        logger.error("HBTU update error: %s\n%s", user_id, error_details)
        await update.message.reply_text("An error occurred while checking updates. Please try again later.")


def set_action_state(update: Update, state: ActionState, message: str):
    user_id = update.message.from_user.id
    sm = SessionManager()
    sm.set_action(user_id, state)
    return message


async def compress_image_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        set_action_state(update, ActionState.WAITING_FOR_IMAGE_COMPRESS, 'Please send the image you want to compress.')
    )


async def compress_pdf_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        set_action_state(update, ActionState.WAITING_FOR_PDF_COMPRESS, 'Please send the PDF you want to compress.')
    )


async def to_pdf_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        set_action_state(update, ActionState.WAITING_FOR_IMAGE_TO_PDF, 'Please send the image to convert to PDF.')
    )


async def to_images_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        set_action_state(update, ActionState.WAITING_FOR_PDF_TO_IMAGES, 'Please send the PDF to convert into images.')
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    text = update.message.text
    sm = SessionManager()

    allowed, message = sm.check_ai_rate_limit(user_id)
    if not allowed:
        await update.message.reply_text(message)
        return

    if message:
        await update.message.reply_text(message)

    sm.add_history(user_id, "user", text)
    sm.record_ai_request(user_id)

    session = sm.get_session(user_id)
    try:
        response_text = generate_response(
            api_key=GEMINI_API_KEY,
            model_name=MODEL_NAME,
            prompt=text,
            conversation_history=session.history
        )
    except Exception as e:
        logger.error("Brain error for user %s: %s", user_id, e)
        response_text = "Sorry, I encountered an error. Please try again."

    sm.add_history(user_id, "model", response_text)

    quota_msg = sm.get_ai_quota(user_id)
    final_response = f"{response_text}\n\n_{quota_msg}_"

    await update.message.reply_text(final_response, parse_mode=ParseMode.MARKDOWN_V2)


async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    sm = SessionManager()
    session = sm.get_session(user_id)

    if session.action_state != ActionState.NONE:
        await process_file_action(update, context, session.action_state)
    else:
        await analyze_file_with_brain(update, context)


async def process_file_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action_state: ActionState):
    user_id = update.message.from_user.id
    sm = SessionManager()

    mapping = {
        ActionState.WAITING_FOR_IMAGE_COMPRESS: ('photo', 'Please send an image file.'),
        ActionState.WAITING_FOR_PDF_COMPRESS: ('document', 'Please send a PDF document.'),
        ActionState.WAITING_FOR_IMAGE_TO_PDF: ('photo', 'Please send an image file.'),
        ActionState.WAITING_FOR_PDF_TO_IMAGES: ('document', 'Please send a PDF document.'),
    }

    expected_type, invalid_msg = mapping.get(action_state, (None, None))
    if not expected_type:
        return

    valid_file = False
    file_id = None

    if expected_type == 'photo' and update.message.photo:
        valid_file = True
        file_id = update.message.photo[-1].file_id
    elif expected_type == 'document' and update.message.document:
        if update.message.document.mime_type == 'application/pdf':
            valid_file = True
            file_id = update.message.document.file_id

    if not valid_file:
        await update.message.reply_text(invalid_msg + "\nOr type /cancel to stop.")
        return

    allowed, file_op_msg = sm.check_file_op_rate_limit(user_id)
    if not allowed:
        await update.message.reply_text(file_op_msg)
        return

    sm.record_file_op(user_id)
    sm.clear_action(user_id)
    await update.message.reply_text(f"File received. Processing...")

    input_path = None
    output_path = None

    try:
        input_path = await extract_file(context.bot, file_id)
        if not input_path:
            raise ValueError("File could not be downloaded.")

        action_funcs = {
            ActionState.WAITING_FOR_IMAGE_COMPRESS: compress_image,
            ActionState.WAITING_FOR_PDF_COMPRESS: compress_pdf,
            ActionState.WAITING_FOR_IMAGE_TO_PDF: convert_image_to_pdf,
            ActionState.WAITING_FOR_PDF_TO_IMAGES: convert_pdf_to_images,
        }
        output_path = action_funcs[action_state](input_path, OUTPUT_DIR)

        if output_path and os.path.exists(output_path):
            if os.path.isdir(output_path):
                await update.message.reply_text("Done. Sending your files...")
                for filename in sorted(os.listdir(output_path)):
                    filepath = os.path.join(output_path, filename)
                    with open(filepath, 'rb') as f:
                        await context.bot.send_document(chat_id=user_id, document=f)
            else:
                await update.message.reply_text("Done. Sending your file...")
                with open(output_path, 'rb') as f:
                    await context.bot.send_document(chat_id=user_id, document=f)
        else:
            await update.message.reply_text("Action failed or no changes were made.")

    except Exception as e:
        logger.error("File action error for user %s: %s", user_id, e)
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
    user_id = update.message.from_user.id
    sm = SessionManager()

    allowed, message = sm.check_ai_rate_limit(user_id)
    if not allowed:
        await update.message.reply_text(message)
        return

    if message:
        await update.message.reply_text(message)

    file_id = None
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document:
        file_id = update.message.document.file_id

    if not file_id:
        await update.message.reply_text("Unsupported file type.")
        return

    await update.message.reply_text('File received, analyzing...')
    sm.record_ai_request(user_id)
    file_path = None

    try:
        file_path = await extract_file(context.bot, file_id)
        if not file_path:
            await update.message.reply_text("Failed to download file.")
            return

        prompt = update.message.caption or "Describe this file. If there are questions, solve them with detailed answers."
        session = sm.get_session(user_id)

        response_text = generate_response(
            api_key=GEMINI_API_KEY,
            model_name=MODEL_NAME,
            prompt=prompt,
            file_path=file_path,
            conversation_history=session.history
        )

        MAX_MSG_LEN = 4096
        if len(response_text) > MAX_MSG_LEN:
            for i in range(0, len(response_text), MAX_MSG_LEN):
                await update.message.reply_text(response_text[i:i+MAX_MSG_LEN])
        else:
            quota_msg = sm.get_ai_quota(user_id)
            full_response = f"{response_text}\n\n_{quota_msg}_"
            await update.message.reply_text(full_response, parse_mode=ParseMode.MARKDOWN_V2)

        sm.add_history(user_id, "model", response_text)

    except Exception as e:
        logger.error("Brain analysis error: %s", e)
        await update.message.reply_text("An error occurred while analyzing the file.")

    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass


async def shutdown_signal_handler(app: Application, sig: int, loop: asyncio.AbstractEventLoop):
    logger.info("Shutdown signal received (signal %d).", sig)
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