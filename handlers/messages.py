import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes

from ai.openrouter_client import generate_response
from config import (
    MAX_TELEGRAM_MSG_LEN,
    OPENROUTER_API_KEY,
    OPENROUTER_APP_NAME,
    OPENROUTER_MODEL,
    OPENROUTER_REFERER,
    OUTPUT_DIR,
)
from services.file_pipeline import (
    cleanup_paths,
    extract_file_id_for_action,
    process_action_file,
    send_output,
)
from session_manager import ActionState, SessionManager

logger = logging.getLogger(__name__)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    user_id = update.message.from_user.id
    text = update.message.text
    sm = SessionManager()

    allowed, message = sm.check_ai_rate_limit(user_id)
    if not allowed:
        await update.message.reply_text(message)
        return
    if message:
        await update.message.reply_text(message)

    sm.record_ai_request(user_id)
    session = sm.get_session(user_id)
    history = list(session.history)

    try:
        response_text = await asyncio.to_thread(
            generate_response,
            OPENROUTER_API_KEY,
            OPENROUTER_MODEL,
            text,
            None,
            None,
            history,
            OPENROUTER_REFERER,
            OPENROUTER_APP_NAME,
        )
    except Exception as exc:
        logger.error("AI response error for user %s: %s", user_id, exc)
        response_text = "Sorry, I encountered an error. Please try again."

    sm.add_history(user_id, "user", text)
    sm.add_history(user_id, "model", response_text)
    quota_msg = sm.get_ai_quota(user_id)
    if len(response_text) > MAX_TELEGRAM_MSG_LEN:
        chunks = [
            response_text[i : i + MAX_TELEGRAM_MSG_LEN]
            for i in range(0, len(response_text), MAX_TELEGRAM_MSG_LEN)
        ]
        for chunk in chunks:
            await update.message.reply_text(chunk)
        await update.message.reply_text(quota_msg)
        return
    await update.message.reply_text(f"{response_text}\n\n{quota_msg}")


async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    user_id = update.message.from_user.id
    sm = SessionManager()
    action_state = sm.get_session(user_id).action_state
    if action_state != ActionState.NONE:
        await _process_file_action(update, context, action_state)
        return
    await _analyze_file_with_ai(update, context)


async def _process_file_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action_state: ActionState) -> None:
    if not update.message:
        return

    user_id = update.message.from_user.id
    sm = SessionManager()

    file_id, validation_error = extract_file_id_for_action(update.message, action_state)
    if not file_id:
        await update.message.reply_text(validation_error or "Invalid file.")
        return

    allowed, file_msg = sm.check_file_op_rate_limit(user_id)
    if not allowed:
        await update.message.reply_text(file_msg)
        return

    sm.record_file_op(user_id)
    sm.clear_action(user_id)
    await update.message.reply_text("File received. Processing...")

    input_path = None
    output_path = None
    try:
        input_path, output_path = await process_action_file(context.bot, file_id, action_state, OUTPUT_DIR)
        if not output_path:
            await update.message.reply_text("Action failed or no changes were made.")
            return
        await update.message.reply_text("Done. Sending your file(s)...")
        await send_output(context.bot, user_id, output_path)
    except Exception as exc:
        logger.error("File action error for user %s: %s", user_id, exc)
        await update.message.reply_text(f"An error occurred: {exc}")
    finally:
        cleanup_paths(input_path, output_path)


async def _analyze_file_with_ai(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

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

    prompt = update.message.caption or "Describe this file and solve any questions found."
    await update.message.reply_text("File received, analyzing...")
    sm.record_ai_request(user_id)
    history = list(sm.get_session(user_id).history)

    file_path = None
    try:
        from media_extractor import extract_file

        file_path = await extract_file(context.bot, file_id)
        if not file_path:
            await update.message.reply_text("Failed to download file.")
            return

        response_text = await asyncio.to_thread(
            generate_response,
            OPENROUTER_API_KEY,
            OPENROUTER_MODEL,
            prompt,
            None,
            file_path,
            history,
            OPENROUTER_REFERER,
            OPENROUTER_APP_NAME,
        )
        sm.add_history(user_id, "user", prompt)
        sm.add_history(user_id, "model", response_text)

        chunks = [
            response_text[i : i + MAX_TELEGRAM_MSG_LEN]
            for i in range(0, len(response_text), MAX_TELEGRAM_MSG_LEN)
        ] or [response_text]
        for chunk in chunks:
            await update.message.reply_text(chunk)

        await update.message.reply_text(sm.get_ai_quota(user_id))
    except Exception as exc:
        logger.error("AI file analysis error for user %s: %s", user_id, exc)
        await update.message.reply_text("An error occurred while analyzing the file.")
    finally:
        cleanup_paths(file_path, None)
