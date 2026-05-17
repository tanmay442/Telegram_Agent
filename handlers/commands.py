import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import HELP_TEXT, OPENROUTER_API_KEY, OPENROUTER_MODEL
from hbtu_updates.cheking_update import check_for_updates
from services.hbtu_service import format_hbtu_updates
from session_manager import ActionState, SessionManager

logger = logging.getLogger(__name__)


def _set_action_state(update: Update, state: ActionState, message: str) -> str:
    if not update.message:
        return message
    user_id = update.message.from_user.id
    SessionManager().set_action(user_id, state)
    return message


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    user_id = update.message.from_user.id
    ai_quota = SessionManager().get_ai_quota(user_id)
    welcome_text = (
        "Hi! I'm ready to assist you.\n\n"
        "Commands:\n"
        "/hbtu_updates - Check for new HBTU circulars\n"
        "/compress_image - Compress an image\n"
        "/compress_pdf - Compress a PDF\n"
        "/to_pdf - Convert image to PDF\n"
        "/to_images - Convert PDF to images\n"
        "/cancel - Cancel current operation\n"
        "/help - Full command list\n\n"
        f"{ai_quota}"
    )
    await update.message.reply_text(welcome_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    user_id = update.message.from_user.id
    ai_quota = SessionManager().get_ai_quota(user_id)
    await update.message.reply_text(f"{HELP_TEXT}\n\n{ai_quota}")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    user_id = update.message.from_user.id
    sm = SessionManager()
    if sm.get_session(user_id).action_state != ActionState.NONE:
        sm.clear_action(user_id)
        logger.info("User %s canceled their action.", user_id)
        await update.message.reply_text("Your current action has been canceled.")
        return
    await update.message.reply_text("You have no active action to cancel.")


async def hbtu_updates_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    user_id = update.message.from_user.id
    sm = SessionManager()
    allowed, rate_message = sm.check_ai_rate_limit(user_id)
    if not allowed:
        await update.message.reply_text(rate_message)
        return
    if rate_message:
        await update.message.reply_text(rate_message)

    await update.message.reply_text("Checking HBTU updates...")
    sm.record_ai_request(user_id)

    try:
        updates = await asyncio.to_thread(check_for_updates)
        formatted = await asyncio.to_thread(
            format_hbtu_updates,
            updates,
            OPENROUTER_API_KEY,
            OPENROUTER_MODEL,
        )
        await update.message.reply_text(formatted, disable_web_page_preview=True)
    except Exception as exc:
        logger.error("HBTU update error for user %s: %s", user_id, exc)
        await update.message.reply_text("An error occurred while checking HBTU updates.")


async def compress_image_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        _set_action_state(
            update,
            ActionState.WAITING_FOR_IMAGE_COMPRESS,
            "Please send the image you want to compress.",
        )
    )


async def compress_pdf_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        _set_action_state(
            update,
            ActionState.WAITING_FOR_PDF_COMPRESS,
            "Please send the PDF you want to compress.",
        )
    )


async def to_pdf_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        _set_action_state(
            update,
            ActionState.WAITING_FOR_IMAGE_TO_PDF,
            "Please send the image to convert to PDF.",
        )
    )


async def to_images_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        _set_action_state(
            update,
            ActionState.WAITING_FOR_PDF_TO_IMAGES,
            "Please send the PDF to convert into images.",
        )
    )
