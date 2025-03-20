import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SCREENSHOTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "screenshots"
)
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
VIDEO_RECORDINGS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "videos"
)

# Create directories if they don't exist
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(VIDEO_RECORDINGS_DIR, exist_ok=True)

# Groq LLM model
GROQ_MODEL = (
    "llama3-8b-8192"  # You can use "llama3-70b-8192" for more advanced capabilities
)

# Target website
TARGET_URL = "https://video-converter.com"

# Timeout settings
DEFAULT_TIMEOUT = 60000  # 60 seconds in milliseconds
