import asyncio
import os
import shutil
from typing import Optional

from telegram import Bot, Message

from FileActions.img_compress import compress_image
from FileActions.img_pdf import convert_image_to_pdf, convert_pdf_to_images
from FileActions.pdf_compress import compress_pdf
from media_extractor import extract_file
from session_manager import ActionState

ACTION_FUNCTIONS = {
    ActionState.WAITING_FOR_IMAGE_COMPRESS: compress_image,
    ActionState.WAITING_FOR_PDF_COMPRESS: compress_pdf,
    ActionState.WAITING_FOR_IMAGE_TO_PDF: convert_image_to_pdf,
    ActionState.WAITING_FOR_PDF_TO_IMAGES: convert_pdf_to_images,
}


def extract_file_id_for_action(message: Message, action_state: ActionState) -> tuple[Optional[str], Optional[str]]:
    if action_state in {
        ActionState.WAITING_FOR_IMAGE_COMPRESS,
        ActionState.WAITING_FOR_IMAGE_TO_PDF,
    }:
        if message.photo:
            return message.photo[-1].file_id, None
        return None, "Please send an image file.\nOr type /cancel to stop."

    if action_state in {
        ActionState.WAITING_FOR_PDF_COMPRESS,
        ActionState.WAITING_FOR_PDF_TO_IMAGES,
    }:
        document = message.document
        if document and document.mime_type == "application/pdf":
            return document.file_id, None
        return None, "Please send a PDF document.\nOr type /cancel to stop."

    return None, "Unknown action state. Please try again."


async def process_action_file(bot: Bot, file_id: str, action_state: ActionState, output_dir: str) -> tuple[str, Optional[str]]:
    input_path = await extract_file(bot, file_id)
    if not input_path:
        raise ValueError("File could not be downloaded.")

    action = ACTION_FUNCTIONS[action_state]
    output_path = await asyncio.to_thread(action, input_path, output_dir)
    return input_path, output_path


async def send_output(bot: Bot, chat_id: int, output_path: str) -> None:
    if os.path.isdir(output_path):
        for filename in sorted(os.listdir(output_path)):
            filepath = os.path.join(output_path, filename)
            with open(filepath, "rb") as f:
                await bot.send_document(chat_id=chat_id, document=f)
        return

    with open(output_path, "rb") as f:
        await bot.send_document(chat_id=chat_id, document=f)


def cleanup_paths(input_path: Optional[str], output_path: Optional[str]) -> None:
    if input_path and os.path.exists(input_path):
        try:
            os.remove(input_path)
        except OSError:
            pass

    if not output_path or output_path == input_path or not os.path.exists(output_path):
        return

    if os.path.isdir(output_path):
        shutil.rmtree(output_path, ignore_errors=True)
        return

    try:
        os.remove(output_path)
    except OSError:
        pass
