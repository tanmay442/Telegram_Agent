import os
import logging
import asyncio
from telegram.ext import Application
from telegram import Bot

logger = logging.getLogger(__name__)
DEFAULT_DOWNLOAD_DIR = "Temp/Cache_Downloaded"


async def extract_file(bot: Bot, file_id: str, download_dir: str = DEFAULT_DOWNLOAD_DIR) -> str | None:
    try:
        file = await bot.get_file(file_id)
        file_name = os.path.basename(file.file_path) or f"file_{file_id}"
        full_download_path = os.path.join(download_dir, file_name)

        os.makedirs(download_dir, exist_ok=True)

        await asyncio.wait_for(
            file.download_to_drive(custom_path=full_download_path),
            timeout=60
        )

        logger.info("Downloaded file to: %s", full_download_path)
        return full_download_path

    except asyncio.TimeoutError:
        logger.error("Download timeout for file_id: %s", file_id)
        return None
    except Exception as e:
        logger.error("Download failed for file_id %s: %s", file_id, e)
        return None