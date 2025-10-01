import os
import logging
import shutil
import asyncio
import dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
import mimetypes


from FileActions.img_compress import compress_image
from FileActions.pdf_compress import compress_pdf
from FileActions.img_pdf import convert_image_to_pdf, convert_pdf_to_images

from Google_serviecs.mail_services import draft_email, read_emails, flag_or_label_mail
from Google_serviecs.caleander_services import create_event, view_events, delete_event
from Google_serviecs.tasks_services import create_task, view_tasks, modify_task, create_task_list

from hbtu_updates.cheking_update import check_for_updates
from media_extractor import extract_file
from Brain import generate_response

dotenv.load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = os.environ.get("MODEL_NAME")

# --- Directory Setup for File Actions ---
OUTPUT_DIR = "Temp/Output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Logging Setup ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


user_histories = {}
user_actions = {}
MAX_HISTORY_LENGTH = 20 # Reduced for practicality with large file data

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message. Uses MarkdownV2 for formatting."""
    welcome_text = (
        "Hi\\! I'm ready to assist\\.\n\n"
        "You can send me a message or a file for AI analysis\\. "
        "I'll remember the file so you can ask follow\\-up questions\\.\n\n"
        "*Available Commands:*\n"
        "`/hbtu_updates` \\- Check for new HBTU circulars\\.\n"
        "`/compress_image` \\- Compresses an image\\.\n"
        "`/compress_pdf` \\- Compresses a PDF\\.\n"
        "`/to_pdf` \\- Converts an image to a PDF\\.\n"
        "`/to_images` \\- Converts a PDF to images\\.\n"
        "`/cancel` \\- Cancel the current file operation\\."
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN_V2)

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancels any pending user action."""
    user_id = update.message.from_user.id
    if user_id in user_actions:
        del user_actions[user_id]
        logger.info(f"User {user_id} canceled their action.")
        await update.message.reply_text("Your current action has been canceled.")
    else:
        await update.message.reply_text("You have no active action to cancel.")

# --- HBTU Update Command Handler ---
async def hbtu_updates_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Checks for HBTU updates, formats them with Gemini, and sends them."""
    user_id = update.message.from_user.id
    await update.message.reply_text("Checking for the latest HBTU updates, this may take a moment...")
    logger.info(f"User {user_id} initiated HBTU update check.")

    try:
        new_updates = await asyncio.to_thread(check_for_updates)
        if not new_updates:
            await update.message.reply_text("No new updates found on the HBTU website.")
            return

        prompt = (
            "Format the following list of new university updates for a Telegram message. "
            "Use Telegram's MarkdownV2 formatting. Escape all special characters like '.' and '-'. "
            "For each item, make its title bold and then provide the link.\n\n"
            "make the updates present in a human readable way like here are the new updates i found\n\n"
            f"Data: {new_updates}"
        )
        formatted_response = generate_response(api_key=GEMINI_API_KEY, model_name=MODEL_NAME, prompt=prompt)
        await update.message.reply_text(formatted_response, parse_mode=ParseMode.MARKDOWN_V2)

    except Exception as e:
        logger.error(f"Error during HBTU update check: {e}")
        await update.message.reply_text("Sorry, an error occurred while checking for updates.")

# --- File Action Logic ---
async def file_action_command(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, message: str):
    """Sets a user's pending file action."""
    user_id = update.message.from_user.id
    user_actions[user_id] = action
    logger.info(f"User {user_id} initiated action: {action}")
    await update.message.reply_text(message)

# --- Command Definitions ---
async def compress_image_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await file_action_command(update, context, 'compress_image', 'Please send the image you want to compress.')
async def compress_pdf_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await file_action_command(update, context, 'compress_pdf', 'Please send the PDF you want to compress.')
async def to_pdf_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await file_action_command(update, context, 'to_pdf', 'Please send the image to convert to a PDF.')
async def to_images_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await file_action_command(update, context, 'to_images', 'Please send the PDF to convert into images.')

# --- History Management ---
def get_user_history(user_id: int) -> list:
    """Retrieves the conversation history for a user."""
    return user_histories.setdefault(user_id, [])

def add_to_history(user_id: int, role: str, text: str = None, file_blob: dict = None):
    """
    Adds a turn to the user's conversation history.
    A turn can contain text, a file blob, or both.
    """
    history = get_user_history(user_id)
    
    parts = []
    if text:
        parts.append(text)
    if file_blob:
        parts.append(file_blob)

    if not parts: # Do not add empty history turns
        return

    history.append({'role': role, 'parts': parts})
    
    # Trim history if it exceeds the maximum length
    if len(history) > MAX_HISTORY_LENGTH:
        user_histories[user_id] = history[-MAX_HISTORY_LENGTH:]

def get_mime_type(file_path: str) -> str:
    """Helper to get the mime type of a file."""
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or "application/octet-stream" # Default if not found

# --- Core Message & Media Handlers ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processes text messages using the Brain module, maintaining context."""
    user_id = update.message.from_user.id
    text = update.message.text
    
    add_to_history(user_id, "user", text=text)
    
    # The history now may contain file context from a previous turn
    response_text = generate_response(
        api_key=GEMINI_API_KEY, 
        model_name=MODEL_NAME, 
        prompt=None, # Prompt is now part of the history
        conversation_history=get_user_history(user_id)
    )
    
    add_to_history(user_id, "model", text=response_text)
    await update.message.reply_text(response_text)

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Routes media to a file action or to the Brain for analysis."""
    user_id = update.message.from_user.id
    action = user_actions.get(user_id)
    if action:
        await process_file_action(update, context, action)
    else:
        await analyze_file_with_brain(update, context)

async def process_file_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
    """Processes a file based on a pending user command with validation."""
    user_id = update.message.from_user.id
    
    action_requirements = {
        'compress_image': {'type': 'photo', 'message': 'Please send an image file for this action.'},
        'to_pdf': {'type': 'photo', 'message': 'Please send an image file for this action.'},
        'compress_pdf': {'type': 'document', 'mime': 'application/pdf', 'message': 'Please send a PDF document for this action.'},
        'to_images': {'type': 'document', 'mime': 'application/pdf', 'message': 'Please send a PDF document for this action.'},
    }
    req = action_requirements[action]
    
    valid_file = False
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
    
    input_path, output_path = None, None
    try:
        input_path = await extract_file(context.bot, file_id)
        if not input_path:
            raise ValueError("File could not be downloaded from Telegram.")

        action_func = {
            'compress_image': compress_image, 'compress_pdf': compress_pdf,
            'to_pdf': convert_image_to_pdf, 'to_images': convert_pdf_to_images
        }[action]
        output_path = action_func(input_path, OUTPUT_DIR)

        if output_path and os.path.exists(output_path):
            if os.path.isdir(output_path):
                await update.message.reply_text("Action complete. Sending your files...")
                for filename in sorted(os.listdir(output_path)):
                    await context.bot.send_document(chat_id=user_id, document=open(os.path.join(output_path, filename), 'rb'))
            else:
                await update.message.reply_text("Action complete. Sending your file...")
                await context.bot.send_document(chat_id=user_id, document=open(output_path, 'rb'))
        else:
            await update.message.reply_text("The action failed or the file was already optimal and no changes were made.")
    except Exception as e:
        logger.error(f"Error during file action '{action}': {e}")
        await update.message.reply_text(f"An error occurred: {e}")
    finally:
        if input_path and os.path.exists(input_path): os.remove(input_path)
        if output_path and output_path != input_path and os.path.exists(output_path):
            if os.path.isdir(output_path): shutil.rmtree(output_path)
            else: os.remove(output_path)

async def analyze_file_with_brain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Analyzes a file with the AI and sets it in the conversation context
    for follow-up questions.
    """
    user_id = update.message.from_user.id
    file_id = update.message.photo[-1].file_id if update.message.photo else update.message.document.file_id
    if not file_id:
        return await update.message.reply_text("File type not suitable for analysis.")

    await update.message.reply_text('File received, analyzing with AI...')
    file_path = None
    try:
        file_path = await extract_file(context.bot, file_id)
        if not file_path:
            raise ValueError("Could not download file.")
            
        # Clear previous history to start a new context with this file
        if user_id in user_histories:
            user_histories[user_id].clear()
            logger.info(f"Cleared history for user {user_id} to start new file context.")

        # Read file into memory
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        file_blob = {
            "mime_type": get_mime_type(file_path),
            "data": file_bytes,
        }
        
        prompt = update.message.caption or "Describe this file in detail. What is it?"

        # Add the initial prompt and the file to the history
        add_to_history(user_id, "user", text=prompt, file_blob=file_blob)

        # Generate the first response
        response_text = generate_response(
            api_key=GEMINI_API_KEY, 
            model_name=MODEL_NAME, 
            prompt=None, # Prompt is now in the history
            file_path=None, # File is now in the history
            conversation_history=get_user_history(user_id)
        )
        
        # Add the AI's first response to the history
        add_to_history(user_id, "model", text=response_text)
        
        await update.message.reply_text(response_text)

    except Exception as e:
        logger.error(f"Error in analyze_file_with_brain: {e}")
        await update.message.reply_text("An error occurred while analyzing the file.")
    finally:
        # Clean up the downloaded file immediately after reading it
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Command Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CommandHandler("hbtu_updates", hbtu_updates_command))
    application.add_handler(CommandHandler("compress_image", compress_image_command))
    application.add_handler(CommandHandler("compress_pdf", compress_pdf_command))
    application.add_handler(CommandHandler("to_pdf", to_pdf_command))
    application.add_handler(CommandHandler("to_images", to_images_command))

    # Message Handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler((filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND, handle_media))

    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()