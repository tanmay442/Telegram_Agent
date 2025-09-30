from PIL import Image
import img2pdf
import fitz  # PyMuPDF
import os
import datetime

def convert_image_to_pdf(image_path, pdf_path):
    #image_path = "input_image.jpg"
    pdf_path = os.path.join(pdf_path,f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

    try:
        # Open the image using Pillow
        image = Image.open(image_path)

        # converting into chunks using img2pdf
        pdf_bytes = img2pdf.convert(image.filename)

        # Write the PDF bytes to a file
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

        print(f"Successfully converted {image_path} to {pdf_path}")

    except FileNotFoundError:
        print(f"Error: Image file not found at {image_path}")
    except Exception as e:
        print(f"An error occurred: {e}")
    
    return pdf_path


##testing purposes
##convert_image_to_pdf("wallpaper.jpg","Temp/temp_pdfs")


def convert_pdf_to_images(pdf_path, output_directory):

    #pdf_path = "example.pdf"
    output_directory=os.path.join(output_directory,f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_images")
    os.makedirs(output_directory, exist_ok=True)

    ##Qua;ity control
    high_res_dpi = 300 

    try:
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            # Render page 
            pix = page.get_pixmap(dpi=high_res_dpi)
            
            # Save the image
            image_path = os.path.join(output_directory, f"page_{i+1}.jpg")
            pix.save(image_path)
        
        doc.close()
        print(f"Converted '{pdf_path}' to high-resolution images in '{output_directory}'")

    except FileNotFoundError:
        print(f"Error: The file '{pdf_path}' was not found")
    except Exception as e:
        print(f"An error occurred: {e}")
    
    return output_directory


##testing purposes
##convert_pdf_to_images("/home/gtanmay/Documents/DOCS/hbtu.pdf","Temp/temp_images")   