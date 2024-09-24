import pytesseract
from PIL import Image

# If Tesseract is not in your PATH, specify the full path to the executable
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Path to the image you uploaded
image_path = 'C:/Users/jacque.debie/source/repos/MT5/MT5CopyTradingV2/downloaded_images/JDB_Copy_Signals_image_264.jpg'

# Open the image file
img = Image.open(image_path)

# Use Tesseract to extract text
text = pytesseract.image_to_string(img)

# Print the extracted text
print("Extracted Text:", text)
