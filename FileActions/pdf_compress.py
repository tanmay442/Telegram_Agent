import os
import io
import shutil
import logging
from datetime import datetime
from PIL import Image
import fitz  # PyMuPDF
from pypdf import PdfReader, PdfWriter

# --- Setup basic logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def _compress_pdf_streams(input_path: str, output_dir: str) -> str:
    
    output_path = os.path.join(output_dir, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_streams_compressed.pdf")
    
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()

        for page in reader.pages:
            writer.add_page(page)
            # This compresses the content streams of the page
            writer.pages[-1].compress_content_streams()

        with open(output_path, "wb") as f:
            writer.write(f)
        return output_path
    except Exception as e:
        logging.error(f"Error during pypdf stream compression: {e}")
        return None

def _compress_pdf_images(input_path: str, output_dir: str, quality: int = 75) -> str:
   
    output_path = os.path.join(output_dir, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_image_compressed.pdf")
    
    try:
        doc = fitz.open(input_path)
        image_found = False

        # Iterate through pages to find and re-compress images
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # get_images(full=True) is the key to finding image references
            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0] # The internal reference to the image
                
                # Extract the base image data
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                # Load the image with PIL and save it back with new quality
                pil_image = Image.open(io.BytesIO(image_bytes))
                img_buffer = io.BytesIO()
                pil_image.save(img_buffer, format="JPEG", quality=quality, optimize=True)
                img_buffer.seek(0)
                
                # Replace the old image with the new compressed one
                page.replace_image(xref, stream=img_buffer)
                image_found = True

        if not image_found:
            logging.warning("No images found to compress in the PDF.")
            doc.close()
            return None # Return None if no images were processed

        # Save the modified PDF with garbage collection to remove old objects
        # This save operation is now OUTSIDE the loop for huge performance gain.
        doc.save(output_path, garbage=4, deflate=True, clean=True)
        doc.close()
        return output_path
    except Exception as e:
        logging.error(f"Error during image re-compression: {e}")
        return None

def compress_pdf(input_path: str, output_dir: str, reduction_threshold: float = 0.75) -> str:
  
    os.makedirs(output_dir, exist_ok=True)
    original_size = os.path.getsize(input_path)
    
    # Fast Stream Compression ---
    logging.info("Attempting fast stream compression...")
    stream_compressed_path = _compress_pdf_streams(input_path, output_dir)
    
    if stream_compressed_path:
        stream_compressed_size = os.path.getsize(stream_compressed_path)
        if stream_compressed_size < original_size * reduction_threshold:
            logging.info(f"Stream compression successful: {original_size/1024:.2f} KB -> {stream_compressed_size/1024:.2f} KB")
            return stream_compressed_path
        else:
            logging.warning("Stream compression was not effective. Removing temporary file.")
            os.remove(stream_compressed_path)

    #  Lossy Image Re-compression 
    logging.info("Stream compression ineffective, attempting image re-compression...")
    image_compressed_path = _compress_pdf_images(input_path, output_dir)
    
    if image_compressed_path:
        image_compressed_size = os.path.getsize(image_compressed_path)
        if image_compressed_size < original_size * reduction_threshold:
            logging.info(f"Image compression successful: {original_size/1024:.2f} KB -> {image_compressed_size/1024:.2f} KB")
            return image_compressed_path
        else:
            logging.warning("Image compression was not effective. Removing temporary file.")
            os.remove(image_compressed_path)

    # Fallback: No effective compression ---
    logging.warning("No compression method was effective. Copying original file.")
    final_path = os.path.join(output_dir, os.path.basename(input_path))
    shutil.copy2(input_path, final_path)
    return final_path

