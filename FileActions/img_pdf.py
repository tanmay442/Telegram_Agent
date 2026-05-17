from PIL import Image
import img2pdf
import fitz
import os
import datetime
import logging

logger = logging.getLogger(__name__)


def convert_image_to_pdf(image_path: str, output_dir: str) -> str | None:
    os.makedirs(output_dir, exist_ok=True)
    file_name = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = os.path.join(output_dir, file_name)

    try:
        with Image.open(image_path) as image:
            pdf_bytes = img2pdf.convert(image.filename)

        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

        logger.info("Converted %s to %s", image_path, pdf_path)
        return pdf_path

    except FileNotFoundError:
        logger.error("Image file not found: %s", image_path)
        return None
    except Exception as e:
        logger.error("Image to PDF conversion error: %s", e)
        return None


def convert_pdf_to_images(pdf_path: str, output_dir: str, dpi: int = 300) -> str | None:
    output_subdir = os.path.join(output_dir, f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_images")
    os.makedirs(output_subdir, exist_ok=True)

    try:
        with fitz.open(pdf_path) as doc:
            page_count = len(doc)
            for i, page in enumerate(doc):
                pix = page.get_pixmap(dpi=dpi)
                image_path = os.path.join(output_subdir, f"page_{i+1}.jpg")
                pix.save(image_path)

        logger.info("Converted %s to %d images in %s", pdf_path, page_count, output_subdir)
        return output_subdir

    except FileNotFoundError:
        logger.error("PDF file not found: %s", pdf_path)
        return None
    except Exception as e:
        logger.error("PDF to images conversion error: %s", e)
        return None
