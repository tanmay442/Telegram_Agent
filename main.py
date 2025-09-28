import sqlite3
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes


# --- Configuration ---
TELEGRAM_TOKEN = "" 
DATABASE_FILE = "user_data.db"

# --- In-memory lists (loaded from DB at startup) ---
# Variable 1: List of all multimedia file_ids stored
media_file_ids = []
# Variable 2: List of all text messages stored
text_messages = []

# --- Database Setup ---
def setup_database():
    """Creates the database and table if they don't exist."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            user_id INTEGER,
            timestamp TEXT,
            message_type TEXT,
            content TEXT
        )
    ''')
    conn.commit()
    conn.close()

# --- Load initial data from DB into memory ---
def load_data_from_db():
    """Populates the in-memory lists from the database on startup."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    for row in cursor.execute("SELECT message_type, content FROM messages"):
        message_type, content = row
        if message_type == 'text':
            text_messages.append(content)
        else:
            media_file_ids.append(content)
    conn.close()
    print(f"Loaded {len(text_messages)} text messages and {len(media_file_ids)} media files from DB.")

# --- The Single Handler for ALL Messages ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catches any message, extracts content, saves to DB, and provides pipe variables."""
    user_id = update.effective_user.id
    timestamp = datetime.now().isoformat()
    message = update.message

    message_type = 'unknown'
    content = None

    # Determine message type and get content/file_id
    if message.text:
        message_type = 'text'
        content = message.text
    elif message.photo:
        message_type = 'photo'
        content = message.photo[-1].file_id  # Get highest quality photo's file_id
    elif message.document:
        message_type = 'document'
        content = message.document.file_id
    elif message.video:
        message_type = 'video'
        content = message.video.file_id
    elif message.audio:
        message_type = 'audio'
        content = message.audio.file_id

    if not content:
        return # Ignore message types we don't handle

    # --- VARIABLE TO PIPE USER INPUT TO YOUR FUNCTIONS ---
    # You can use 'content' and 'user_id' here to call your own functions
    # For example: process_image(content) or analyze_text(user_id, content)
    user_input_to_process = content
    print(f"Processing input: {user_input_to_process}")

    # --- Store in Database ---
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (user_id, timestamp, message_type, content) VALUES (?, ?, ?, ?)",
        (user_id, timestamp, message_type, content)
    )
    conn.commit()
    conn.close()

    # --- Update in-memory lists ---
    if message_type == 'text':
        text_messages.append(content)
    else:
        media_file_ids.append(content)

    # --- VARIABLE FOR BOT'S RESPONSE OUTPUT ---
    # This is the output you can customize and pipe to the user
    output_variable = f"✅ Stored! Total text: {len(text_messages)}, Total media: {len(media_file_ids)}"
    await message.reply_text(output_variable)

# --- Main Bot Execution ---
def main() -> None:
    # Initial setup
    setup_database()
    load_data_from_db()

    # Create the bot application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add the single handler for all message types (except commands)
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    # Start the bot
    print("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()