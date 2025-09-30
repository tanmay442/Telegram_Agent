from PIL import Image
import os
import io
import datetime

def compress_image(input_path, output_dir, max_size=500, quality=95):
    """
    Compresses an image to be under a certain size.
    Returns the path to the compressed file, or the original path if no compression was needed.
    Returns None on failure.
    """
    # Define a unique output path within the output directory
    file_name = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_compressed.jpg"
    output_path = os.path.join(output_dir, file_name)

    max_size_bytes = max_size * 1024

    try:
        original_size_bytes = os.path.getsize(input_path)
        if original_size_bytes <= max_size_bytes:
            print(f"Image is already under {max_size} KB. No compression needed.")
            return input_path  # Return the ORIGINAL path

        with Image.open(input_path) as img:
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            img_buffer = io.BytesIO()
            
            current_quality = quality
            while current_quality > 10:
                img.save(img_buffer, "JPEG", optimize=True, quality=current_quality)
                
                if img_buffer.tell() <= max_size_bytes:
                    with open(output_path, "wb") as f:
                        f.write(img_buffer.getvalue())
                    print(f"Compressed successfully. Saved to '{output_path}'")
                    return output_path  # Return the NEW path
                
                # Reset buffer for next attempt
                img_buffer.seek(0)
                img_buffer.truncate(0)
                current_quality -= 5

            print("Could not compress to the target size.")
            return None

    except Exception as e:
        print(f"An error occurred during image compression: {e}")
        return None