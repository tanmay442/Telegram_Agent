from PIL import Image
import os
import io
import datetime

def compress_image(input_path, output_path, max_size=500 ,quality=95):
    
    output_path=os.path.join(output_path,f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_compressed.jpg")

    max_size_bytes = max_size * 1024

    original_size_bytes = os.path.getsize(input_path)
    if original_size_bytes <= max_size_bytes:
        print(f"Image is already under {max_size} KB ")
        return True
    try:
        with Image.open(input_path) as img:
            # non-JPEG modes for compatibility
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            #in meomry bufer to check file size without saving
            img_buffer = io.BytesIO()
    
        while True:
            quality -= 5
            if quality < 10:
                print("Cannot compress image to the desired size without going below quality threshold.")
                return False
            
            # save image to the in memory bufer
            img.save(img_buffer, "JPEG", optimize=True, quality=quality)

            # check bufer size
            img_buffer_size = img_buffer.tell()


            if img_buffer_size <= max_size_bytes:
                 # good compression level, save the bufer 
                    with open(output_path, "wb") as f:
                        f.write(img_buffer.getvalue())

                    original_size_mb = original_size_bytes / (1024 * 1024)
                    compressed_size_kb = img_buffer_size / 1024


                    print(f"Original size: {original_size_mb:.2f} MB")
                    print(f"Compressed size: {compressed_size_kb:.2f} KB (Quality: {quality})")
                    print(f"File saved to '{output_path}'")
                    return True
            
            # Reset the buffer for the next iteration
            img_buffer.seek(0)
            img_buffer.truncate(0)
            


    except Exception as e:
        print(f"An error occurred: {e}")
        return False
    
    return output_path

    
##TESTING PURPOSES
###compress_image("/home/gtanmay/Pictures/p.png","Temp/temp_images/cache",)