import time
import os
from playwright.sync_api import sync_playwright
from datetime import datetime
from models.test_result import TestResult, TestStep
from utils.screenshot import take_screenshot
from utils.logger import setup_logger
from config import DEFAULT_TIMEOUT, TARGET_URL, VIDEO_RECORDINGS_DIR


class PlaywrightService:
    def __init__(self, record_video=False, headless=True):
        self.playwright = None
        self.browser = None
        self.context = None
        self.record_video = record_video
        self.headless = headless
        self.video_path = None

    def __enter__(self):
        self.playwright = sync_playwright().start()
        # Launch browser with appropriate options
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=["--disable-web-security", "--no-sandbox", "--disable-gpu"],
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")

    def create_page(self, test_name, youtube_url):
        # Generate a unique timestamp for the video file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_filename = f"{test_name}_{timestamp}.webm"
        video_path = os.path.join(VIDEO_RECORDINGS_DIR, video_filename)

        # Ensure video directory exists
        os.makedirs(VIDEO_RECORDINGS_DIR, exist_ok=True)

        # Store video path for later reference
        self.video_path = video_path if self.record_video else None

        # Create browser context with recording options if enabled
        context_options = {
            "viewport": {"width": 1280, "height": 720},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
        }

        if self.record_video:
            # Configure video recording
            context_options["record_video_dir"] = VIDEO_RECORDINGS_DIR
            context_options["record_video_size"] = {"width": 1280, "height": 720}

        # Create context and store it for later cleanup
        self.context = self.browser.new_context(**context_options)

        # Enable request/response logging for debugging
        self.context.on(
            "request", lambda request: print(f">> {request.method} {request.url}")
        )
        self.context.on(
            "response", lambda response: print(f"<< {response.status} {response.url}")
        )

        # Add event listener for console logs
        self.context.on(
            "console", lambda msg: print(f"CONSOLE: {msg.type}: {msg.text}")
        )

        # Create page with extended permissions
        page = self.context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)

        # Grant permissions that might be needed
        self.context.grant_permissions(["geolocation", "notifications"])

        return page, self.video_path

    def execute_test(self, test_func, youtube_url: str, test_name: str):
        """Execute a test function within the Playwright context with optional video recording"""
        logger, log_path = setup_logger(test_name, youtube_url)

        # Create test result object
        test_result = TestResult(
            test_name=test_name,
            youtube_url=youtube_url,
            steps=[],
            start_time=datetime.now(),
        )

        try:
            # Create a new page and get the video path if recording is enabled
            page, video_path = self.create_page(test_name, youtube_url)

            # Set the video path in the test result if recording
            if self.record_video and video_path:
                test_result.video_path = video_path
                logger.info(f"Recording video to: {video_path}")

            # Execute the test
            logger.info(f"Starting test: {test_name} with URL: {youtube_url}")
            test_func(page, youtube_url, logger, test_result)

            # Wait for any pending operations to complete
            time.sleep(5)

            # Complete the test
            test_result.complete("success")
            logger.info(f"Test completed successfully")

        except Exception as e:
            logger.error(f"Test failed with error: {str(e)}")

            # Add failure step
            error_step = TestStep(
                name="test_execution_failed", status="error", error_message=str(e)
            )
            test_result.add_step(error_step)

            # Complete the test with failure status
            test_result.complete("error")

        finally:
            # Ensure the context is closed to save the video
            if self.context:
                # Wait a moment before closing to ensure video is properly saved
                time.sleep(3)
                try:
                    self.context.close()
                    logger.info("Browser context closed")
                except Exception as close_error:
                    logger.error(f"Error closing browser context: {str(close_error)}")

        return test_result, log_path
