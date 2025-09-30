import os
from telegram.ext import Application
from telegram import Bot

async def extract_file(bot: Bot, file_id: str, download_dir="Temp/Cache_Downloaded") -> str | None:
   
    try:
        
        file = await bot.get_file(file_id)

        
        file_name = os.path.basename(file.file_path)
        full_download_path = os.path.join(download_dir, file_name)

        
        os.makedirs(download_dir, exist_ok=True)

        
        await file.download_to_drive(custom_path=full_download_path)

        
        return full_download_path

    except Exception as e:
        print(f"An error occurred while downloading file_id {file_id}: {e}")
        return None



