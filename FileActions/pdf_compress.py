import os
import io
import shutil
import logging
from datetime import datetime
from PIL import Image
import fitz
from pypdf import PdfReader, PdfWriter

logger = logging.getLogger(__name__)


def _compress_pdf_streams(input_path: str, output_dir: str) -> str | None:
    output_path = os.path.join(output_dir, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_streams_compressed.pdf")

    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()

        for page in reader.pages:
            writer.add_page(page)
            writer.pages[-1].compress_content_streams()

        with open(output_path, "wb") as f:
            writer.write(f)
        return output_path
    except Exception as e:
        logger.error("Stream compression error: %s", e)
        return None


def _compress_pdf_images(input_path: str, output_dir: str, quality: int = 75) -> str | None:
    output_path = os.path.join(output_dir, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_image_compressed.pdf")

    try:
        doc = fitz.open(input_path)
        image_found = False

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)

            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]

                pil_image = Image.open(io.BytesIO(image_bytes))
                img_buffer = io.BytesIO()
                pil_image.save(img_buffer, format="JPEG", quality=quality, optimize=True)
                img_buffer.seek(0)

                page.replace_image(xref, stream=img_buffer)
                image_found = True

        if not image_found:
            logger.warning("No images found to compress in PDF.")
            doc.close()
            return None

        doc.save(output_path, garbage=4, deflate=True, clean=True)
        doc.close()
        return output_path
    except Exception as e:
        logger.error("Image compression error: %s", e)
        return None


def compress_pdf(input_path: str, output_dir: str, reduction_threshold: float = 0.75) -> str:
    os.makedirs(output_dir, exist_ok=True)
    original_size = os.path.getsize(input_path)

    logger.info("Attempting stream compression...")
    stream_compressed_path = _compress_pdf_streams(input_path, output_dir)

    if stream_compressed_path:
        stream_compressed_size = os.path.getsize(stream_compressed_path)
        if stream_compressed_size < original_size * reduction_threshold:
            logger.info("Stream compression: %.2f KB -> %.2f KB", original_size / 1024, stream_compressed_size / 1024)
            return stream_compressed_path
        else:
            logger.warning("Stream compression ineffective, removing temp file.")
            os.remove(stream_compressed_path)

    logger.info("Attempting image re-compression...")
    image_compressed_path = _compress_pdf_images(input_path, output_dir)

    if image_compressed_path:
        image_compressed_size = os.path.getsize(image_compressed_path)
        if image_compressed_size < original_size * reduction_threshold:
            logger.info("Image compression: %.2f KB -> %.2f KB", original_size / 1024, image_compressed_size / 1024)
            return image_compressed_path
        else:
            logger.warning("Image compression ineffective, removing temp file.")
            os.remove(image_compressed_path)

    logger.warning("No compression effective, copying original.")
    final_path = os.path.join(output_dir, os.path.basename(input_path))
    shutil.copy2(input_path, final_path)
    return final_path