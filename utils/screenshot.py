import os
import time
from datetime import datetime
from playwright.sync_api import Page
from config import SCREENSHOTS_DIR


def take_screenshot(page: Page, step_name: str, test_name: str):
    """Take a screenshot and save it to the screenshots directory"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{test_name}_{step_name}_{timestamp}.png"
    filepath = os.path.join(SCREENSHOTS_DIR, filename)

    # Ensure the directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # Take the screenshot
    page.screenshot(path=filepath)

    return filepath
