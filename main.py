from FileActions.img_compress import compress_image
from FileActions.pdf_compress import compress_pdf
from FileActions.img_pdf import convert_image_to_pdf, convert_pdf_to_images

from Google_serviecs.mail_services import draft_email , read_emails , flag_or_label_mail
from Google_serviecs.caleander_services import create_event, view_events, delete_event
from Google_serviecs.tasks_services import create_task , view_tasks , modify_task , create_task_list

from hbtu_updates.cheking_update import check_for_updates

from media_extractor import extract_file

from Brain import generate_response

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import logging


# Enable logging to see errors and bot activity
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# A dictionary to store user chat histories
user_histories = {}
MAX_HISTORY_LENGTH = 50

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text('Hi! I will store your messages and media file IDs.')

def get_user_history(user_id: int) -> list:
    """Retrieves or creates a chat history for a given user."""
    if user_id not in user_histories:
        user_histories[user_id] = []
    return user_histories[user_id]

def add_to_history(user_id: int, item: str):
    """Adds an item to the user's chat history and maintains the maximum length."""
    history = get_user_history(user_id)
    history.append(item)
    if len(history) > MAX_HISTORY_LENGTH:
        user_histories[user_id] = history[-MAX_HISTORY_LENGTH:]
    

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stores text messages and responds."""
    user_id = update.message.from_user.id
    text = update.message.text
    add_to_history(user_id, f"Message: {text}")
    await update.message.reply_text('message read')
    logger.info(f"User {user_id} sent a text message. History size: {len(get_user_history(user_id))}")
    print(user_histories)

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stores media file IDs and responds."""
    user_id = update.message.from_user.id
    file_id = None
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        add_to_history(user_id, f"Photo ID: {file_id}")
    elif update.message.video:
        file_id = update.message.video.file_id
        add_to_history(user_id, f"Video ID: {file_id}")
    elif update.message.document:
        file_id = update.message.document.file_id
        add_to_history(user_id, f"Document ID: {file_id}")
    elif update.message.audio:
        file_id = update.message.audio.file_id
        add_to_history(user_id, f"Audio ID: {file_id}")
    elif update.message.voice:
        file_id = update.message.voice.file_id
        add_to_history(user_id, f"Voice ID: {file_id}")
    elif update.message.sticker:
        file_id = update.message.sticker.file_id
        add_to_history(user_id, f"Sticker ID: {file_id}")

    if file_id:
        await update.message.reply_text('file recieved')
        logger.info(f"User {user_id} sent a media file. History size: {len(get_user_history(user_id))}")

def main() -> None:
    """Start the bot."""
    # Replace 'YOUR_TOKEN' with your bot's API token.
    application = Application.builder().token("8363793520:AAHNlg2WsHeN79-nFUdbVukjo8_pDNGGnd4").build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.AUDIO | filters.VOICE | filters.Sticker.ALL, handle_media))    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == '__main__':
    main()




