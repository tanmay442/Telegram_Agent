from pypdf import PdfReader, PdfWriter
import os
import datetime
from PIL import Image
import fitz  # PyMuPDF
import io

def apply_pypdf_compression(input_path, output_path):

    output_path=os.path.join(output_path,f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_compressed.pdf")
    
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)
        writer.pages[-1].compress_content_streams()

        

    with open(output_path, "wb") as f:
        writer.write(f)
    
    return output_path
    
  
def iterative_image_compression(input_pdf_path, output_path, quality=75):

    output_path=os.path.join(output_path,f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_compressed_iterative.pdf")   

    doc=fitz.open(input_pdf_path)# pdf to be processed

    com_pdf=fitz.open()#empty pdf for compressed pages

    for i in range(len(doc)):
        page=doc.load_page(i) #load page


        pix = page.get_pixmap(dpi=250)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


        #initing the bufer
        img_buffer = io.BytesIO()
        img.save (img_buffer, format="JPEG", quality=quality)
        img_buffer.seek(0)

        #adding new page with compressed image
        new_page = com_pdf.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(page.rect, stream=img_buffer)
        
        #freeing the bufer
        img_buffer.close()
    
        #saving the compressed pdf(I have no idea what this line does but it is necassary acc to docs )
        com_pdf.save(output_path, garbage=4, deflate=True)

    com_pdf.close()
    doc.close()

    return output_path
   

def compress_pdf(input_path, output_path):

    # First try pypdf compression
    compressed_path = apply_pypdf_compression(input_path, output_path)
    
    # Check if the size is reduced
    original_size = os.path.getsize(input_path)
    compressed_size = os.path.getsize(compressed_path)

    if compressed_size < original_size*0.8:
        print(f"PDF compressed using pypdf: {original_size/1024:.2f} KB -> {compressed_size/1024:.2f} KB")
        return compressed_path
    else:
        os.remove(compressed_path)  # Remove the ineffective compressed file
        print("pypdf compression did not reduce size, trying iterative image compression...")
        # If not reduced, try iterative image compression
        compressed_path_iter = iterative_image_compression(input_path, output_path)
        compressed_size_iter = os.path.getsize(compressed_path_iter)

        if compressed_size_iter < original_size:
            print(f"PDF compressed using iterative image compression: {original_size/1024:.2f} KB -> {compressed_size_iter/1024:.2f} KB")
            return compressed_path_iter
        else:
            print("Iterative image compression also did not reduce size. Keeping original.")
            return input_path  # Return original if no method worked


##Testing Purposess        
##compress_pdf("/home/gtanmay/Documents/DOCS/hbtu.pdf","Temp/temp_pdfs/cache")