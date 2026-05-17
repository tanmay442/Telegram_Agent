from PIL import Image
import os
import io
import datetime
import logging
from PIL import ImageOps

logger = logging.getLogger(__name__)


def compress_image(input_path: str, output_dir: str, max_size: int = 500, quality: int = 85) -> str | None:
    os.makedirs(output_dir, exist_ok=True)
    file_name = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_compressed.jpg"
    output_path = os.path.join(output_dir, file_name)
    max_size_bytes = max_size * 1024

    try:
        original_size_bytes = os.path.getsize(input_path)
        if original_size_bytes <= max_size_bytes:
            logger.info("Image already under %d KB, returning original.", max_size)
            return input_path

        with Image.open(input_path) as original_img:
            img = ImageOps.exif_transpose(original_img)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            img_buffer = io.BytesIO()
            current_quality = quality

            while current_quality > 10:
                img_buffer.seek(0)
                img_buffer.truncate(0)
                img.save(img_buffer, "JPEG", optimize=True, quality=current_quality)

                if img_buffer.tell() <= max_size_bytes:
                    with open(output_path, "wb") as f:
                        f.write(img_buffer.getvalue())
                    logger.info("Compressed successfully: %s", output_path)
                    return output_path

                current_quality -= 5

            logger.warning("Could not compress to target size.")
            return None

    except Exception as e:
        logger.error("Image compression error: %s", e)
        return None
