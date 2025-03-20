import pytesseract
from PIL import Image
import os
import logging
import unicodedata
import re


def extract_text_from_image(image_path):
    """
    Extract text from an image using Tesseract OCR

    Args:
        image_path (str): Path to the image file

    Returns:
        str: Extracted text from the image
    """
    logger = logging.getLogger(__name__)

    if not os.path.exists(image_path):
        logger.error(f"Image file not found: {image_path}")
        return "Image file not found"

    try:
        # Open the image
        image = Image.open(image_path)

        # Extract text using pytesseract
        text = pytesseract.image_to_string(image)

        # Close the image
        image.close()

        # Normalize and sanitize text to avoid special character issues
        normalized_text = unicodedata.normalize("NFKD", text)
        ascii_text = normalized_text.encode("ascii", "ignore").decode("ascii")

        return ascii_text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from image: {str(e)}")
        return f"OCR Error: {str(e)}"


def sanitize_ocr_text(text):
    """
    Sanitize OCR text by removing non-ASCII characters
    or replacing them with ASCII equivalents

    Args:
        text (str): OCR text to sanitize

    Returns:
        str: Sanitized text with only ASCII characters
    """
    if not text:
        return ""

    # Remove non-ASCII characters
    cleaned_text = re.sub(r"[^\x00-\x7F]+", " ", text)

    # Normalize whitespace
    cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()

    return cleaned_text
