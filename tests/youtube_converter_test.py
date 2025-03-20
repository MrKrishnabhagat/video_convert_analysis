import time
from playwright.sync_api import Page, TimeoutError, expect
from models.test_result import TestResult, TestStep
from utils.screenshot import take_screenshot
from utils.ocr import extract_text_from_image
from services.groq_service import GroqService
from config import TARGET_URL


def run_standard_youtube_conversion_test(
    page: Page, youtube_url: str, logger, test_result: TestResult
):
    """
    Standard test implementation for YouTube video conversion with support for URL prompt dialog
    and OCR text analysis at key steps to detect errors
    """
    groq_service = GroqService()

    # Step 1: Navigate to the website
    try:
        logger.info(f"Navigating to {TARGET_URL}")
        page.goto(TARGET_URL)
        # Ensure page is fully loaded
        page.wait_for_load_state("networkidle", timeout=30000)

        # SCREENSHOT 1: After navigation to site
        screenshot_path = take_screenshot(page, "site_navigation", "youtube_converter")

        # Extract text using OCR and check for errors
        ocr_text = extract_text_from_image(screenshot_path)
        logger.info(f"OCR Text from navigation screenshot: {ocr_text}")

        # Check for errors in OCR text using Groq
        error_result = groq_service.check_screenshot_for_errors(
            ocr_text, "site navigation"
        )

        # Add OCR text to step metadata
        metadata = {"ocr_text": ocr_text}

        if error_result.get("error", False):
            error_message = error_result.get(
                "message", "Unknown error detected in OCR text"
            )
            logger.error(f"Error detected in navigation: {error_message}")
            test_result.add_step(
                TestStep(
                    name="navigate_to_site",
                    status="error",
                    error_message=error_message,
                    screenshot_path=screenshot_path,
                    metadata=metadata,
                )
            )
            raise Exception(f"Navigation error: {error_message}")

        test_result.add_step(
            TestStep(
                name="navigate_to_site",
                status="success",
                screenshot_path=screenshot_path,
                metadata=metadata,
            )
        )
        logger.info("Successfully navigated to the site")
    except Exception as e:
        logger.error(f"Failed to navigate to site: {str(e)}")
        test_result.add_step(
            TestStep(name="navigate_to_site", status="error", error_message=str(e))
        )
        raise

    # Step 2: Click the URL link to open the prompt
    try:
        logger.info("Clicking on URL link to open prompt")

        # Force visibility check before proceeding
        page.wait_for_load_state("domcontentloaded")
        time.sleep(2)  # Additional wait to ensure UI elements are interactive

        # Look for the URL link with various selectors
        url_link_selectors = [
            "a#open_link",
            "a.item_url",
            "a:has-text('URL')",
            ".item.url",
            "a[href='#']:has-text('URL')",
            "button:has-text('URL')",
            "div.url-button",
            "[data-testid='url-input']",
            ".url-section button",
            ".url-tab",
        ]

        url_link = None
        found_selector = None
        for selector in url_link_selectors:
            try:
                # Use wait_for_selector with a short timeout to check existence
                url_link = page.wait_for_selector(
                    selector, timeout=3000, state="visible"
                )

                if url_link:
                    logger.info(f"Found URL link with selector: {selector}")
                    found_selector = selector
                    break
            except:
                continue

        if not url_link:
            # Try a broader approach if specific selectors don't work
            logger.info("Trying to find URL link with broader approach")
            elements = page.query_selector_all("a, button, div.clickable")
            for element in elements:
                text = element.inner_text().lower()
                if "url" in text:
                    url_link = element
                    logger.info("Found URL link by text content")
                    break

        if not url_link:
            raise Exception("Could not find URL link element")

        # Take screenshot with the element highlighted before clicking
        logger.info(f"Clicking URL link element: {found_selector}")

        # Set up dialog handler before clicking
        dialog_triggered = False

        def handle_dialog(dialog):
            nonlocal dialog_triggered
            dialog_triggered = True
            logger.info(f"Dialog detected: {dialog.message}")
            dialog.accept(youtube_url)

        page.once("dialog", handle_dialog)

        # Try alternative click methods if the first one fails
        try:
            # Try dispatching mouse events directly
            page.evaluate(
                """(elem) => {
                    const event = new MouseEvent('click', {
                        bubbles: true,
                        cancelable: true,
                        view: window
                    });
                    elem.dispatchEvent(event);
                }""",
                url_link,
            )

            # Take screenshot after alternative click

        except Exception as e:
            logger.warning(f"Alternative click method also failed: {e}")

        # Take screenshot after click attempts
        screenshot_path = take_screenshot(page, "click_url_link", "youtube_converter")

        test_result.add_step(
            TestStep(
                name="click_url_link", status="success", screenshot_path=screenshot_path
            )
        )
        logger.info("URL link clicked")

    except Exception as e:
        logger.error(f"Failed to click URL link: {str(e)}")
        test_result.add_step(
            TestStep(
                name="click_url_link",
                status="error",
                error_message=str(e),
                screenshot_path=take_screenshot(
                    page, "url_link_error", "youtube_converter"
                ),
            )
        )
        raise

    # Step 3: Input YouTube URL in the prompt dialog
    try:

        logger.info(f"Inputting YouTube URL in prompt: {youtube_url}")
        input_field_needed = page.evaluate(
            """() => {
            // Check if there appears to be a modal or dialog with input field
            const inputs = document.querySelectorAll('input[type="url"], input[type="text"], textarea');
            const visibleInputs = Array.from(inputs).filter(input => {
                const style = window.getComputedStyle(input);
                return style.display !== 'none' && style.visibility !== 'hidden';
            });
            return visibleInputs.length > 0;
        }"""
        )

        logger.info(f"Input field needed: {input_field_needed}")

        if input_field_needed:
            # Enhanced approach to find the input field
            selectors = [
                "input[type='url']",
                "input[placeholder*='URL']",
                "textarea[placeholder*='URL']",
                ".prompt input",
                "dialog input",
                "input.url-input",
                "[data-testid='url-input']",
                "form input",
                ".url-form input",
                "input:visible",
                ".modal input",
                ".popup input",
                "input[type='text']",
            ]

            prompt_input = None

            if prompt_input:
                # Focus the input first
                prompt_input.focus()
                prompt_input.click()

                # Clear any existing text first and fill with value
                prompt_input.fill("")
                time.sleep(0.5)
                prompt_input.type(
                    youtube_url, delay=50
                )  # Type with delay to ensure stability
                time.sleep(1)  # Give time for the value to register

        test_result.add_step(
            TestStep(
                name="input_youtube_url",
                status="success",
                screenshot_path=screenshot_path,
            )
        )
        logger.info("YouTube URL input step completed")

    except Exception as e:
        logger.error(f"Failed to input YouTube URL: {str(e)}")
        test_result.add_step(
            TestStep(
                name="input_youtube_url",
                status="error",
                error_message=str(e),
                screenshot_path=take_screenshot(
                    page, "input_url_error", "youtube_converter"
                ),
            )
        )
        raise

    # Step 4: Set MP4 as output format (if needed)
    try:
        logger.info("Setting MP4 as output format")

        # Wait for page to update after URL submission
        time.sleep(3)
        page.wait_for_load_state("networkidle", timeout=10000)

        # Check if format selection exists
        format_selectors = [
            "select",
            ".format-selection",
            "button:has-text('MP4')",
            "[data-format='mp4']",
            ".format-option:has-text('MP4')",
            ".mp4-option",
        ]

        format_selector = None
        for selector in format_selectors:
            try:
                format_selector = page.wait_for_selector(
                    selector, timeout=2000, state="visible"
                )
                if format_selector:
                    logger.info(f"Found format selector with: {selector}")
                    break
            except:
                continue

        if format_selector:
            format_selector.click()
            time.sleep(1)

            # Try to select MP4 from dropdown if it exists
            mp4_selectors = [
                "option:has-text('MP4')",
                "li:has-text('MP4')",
                "[value='mp4']",
                ".dropdown-item:has-text('MP4')",
            ]

            for selector in mp4_selectors:
                try:
                    mp4_option = page.wait_for_selector(selector, timeout=1000)
                    if mp4_option:
                        mp4_option.click()
                        logger.info("Selected MP4 format")
                        break
                except:
                    continue

        screenshot_path = take_screenshot(page, "select_format", "youtube_converter")
        test_result.add_step(
            TestStep(
                name="select_mp4_format",
                status="success",
                screenshot_path=screenshot_path,
            )
        )
        logger.info("Selected MP4 format (if available)")
    except Exception as e:
        logger.info(
            f"Could not explicitly select MP4 format, may be using default: {str(e)}"
        )
        test_result.add_step(
            TestStep(
                name="select_mp4_format",
                status="warning",
                error_message="Could not explicitly select MP4 format, may be using default",
                screenshot_path=take_screenshot(
                    page, "select_format_warning", "youtube_converter"
                ),
            )
        )
        # Don't raise exception here as this step might not be necessary

    # Step 5: Click convert button - SCREENSHOT 2: Before clicking convert button
    try:
        logger.info("Preparing to click convert button")

        # Wait for any transitions to complete
        time.sleep(2)

        # SCREENSHOT 2: Before clicking convert button
        screenshot_path = take_screenshot(
            page, "before_convert_click", "youtube_converter"
        )

        # Extract text using OCR and check for errors
        ocr_text = extract_text_from_image(screenshot_path)
        logger.info(f"OCR Text before clicking convert: {ocr_text}")

        # Add OCR text to step metadata
        metadata = {"ocr_text": ocr_text}

        # Check for errors in OCR text using Groq
        error_result = groq_service.check_screenshot_for_errors(
            ocr_text, "before conversion"
        )

        if error_result.get("error", False):
            error_message = error_result.get(
                "message", "Unknown error detected in OCR text"
            )
            logger.error(f"Error detected before convert click: {error_message}")
            test_result.add_step(
                TestStep(
                    name="before_convert_button",
                    status="error",
                    error_message=error_message,
                    screenshot_path=screenshot_path,
                    metadata=metadata,
                )
            )
            raise Exception(f"Pre-conversion error: {error_message}")

        # Proceed with finding and clicking the convert button after error check passes
        logger.info("Clicking convert button")

        # Enhanced selectors for convert button
        convert_button_selectors = [
            ".button_1_smaller",
        ]

        convert_button = None
        for selector in convert_button_selectors:
            try:
                convert_button = page.wait_for_selector(
                    selector, timeout=2000, state="visible"
                )
                if convert_button:
                    logger.info(f"Found convert button with selector: {selector}")
                    break
            except:
                continue

        if not convert_button:
            # Try more generic approach if specific selectors don't work
            logger.info("Using generic approach to find convert button")
            buttons = page.query_selector_all("button")
            for button in buttons:
                try:
                    text = button.inner_text().lower()
                    if "convert" in text or "download" in text or "start" in text:
                        convert_button = button
                        logger.info(f"Found convert button with text: {text}")
                        break
                except:
                    continue

        if convert_button:
            # Click with force option and wait
            convert_button.click(force=True)
            time.sleep(2)

            screenshot_path = take_screenshot(
                page, "click_convert", "youtube_converter"
            )
            test_result.add_step(
                TestStep(
                    name="click_convert_button",
                    status="success",
                    screenshot_path=screenshot_path,
                    metadata=metadata,
                )
            )
            logger.info("Successfully clicked convert button")
        else:
            # Try JavaScript approach if button not found
            logger.info("No convert button found, trying JavaScript method")
            result = page.evaluate(
                """() => {
                // Try to find functions that might start conversion
                if (typeof startConversion !== 'undefined') {
                    startConversion();
                    return true;
                }
                if (typeof convertVideo !== 'undefined') {
                    convertVideo();
                    return true;
                }
                // Look for buttons with conversion-related text
                const buttons = document.querySelectorAll('button');
                for (const button of buttons) {
                    if (button.innerText.toLowerCase().includes('convert') || 
                        button.innerText.toLowerCase().includes('download') ||
                        button.innerText.toLowerCase().includes('start')) {
                        button.click();
                        return true;
                    }
                }
                return false;
            }"""
            )

            if result:
                logger.info("Successfully triggered conversion via JavaScript")
                screenshot_path = take_screenshot(
                    page, "js_convert", "youtube_converter"
                )
                test_result.add_step(
                    TestStep(
                        name="click_convert_button",
                        status="success",
                        screenshot_path=screenshot_path,
                        metadata=metadata,
                    )
                )
            else:
                take_screenshot(page, "convert_button_not_found", "youtube_converter")
                raise Exception("Could not find convert button")
    except Exception as e:
        logger.error(f"Failed to click convert button: {str(e)}")
        test_result.add_step(
            TestStep(
                name="click_convert_button",
                status="error",
                error_message=str(e),
                screenshot_path=take_screenshot(
                    page, "convert_button_error", "youtube_converter"
                ),
            )
        )
        raise

    # Step 6: Wait for conversion process
    try:
        logger.info("Waiting for conversion process")

        # Wait for page to settle
        page.wait_for_load_state("networkidle", timeout=10000)

        # Look for common progress indicators
        progress_indicator = None
        selectors = [
            "progress",
            ".progress-bar",
            ".loading",
            ".converting",
            "div[role='progressbar']",
            ".loader",
            ".spinner",
            ".progress",
            ".conversion-progress",
        ]

        for selector in selectors:
            try:
                progress_indicator = page.wait_for_selector(
                    selector, timeout=5000, state="visible"
                )
                if progress_indicator:
                    logger.info(f"Found progress indicator with selector: {selector}")
                    break
            except:
                continue

        if progress_indicator:
            # Take screenshot of progress
            screenshot_path = take_screenshot(
                page, "conversion_progress", "youtube_converter"
            )
            test_result.add_step(
                TestStep(
                    name="conversion_in_progress",
                    status="success",
                    screenshot_path=screenshot_path,
                )
            )

            # Wait for progress to disappear or timeout
            try:
                logger.info(f"Waiting for conversion to complete")
                # Wait for either the progress indicator to disappear OR a success element to appear
                max_wait_time = 120  # seconds
                start_time = time.time()

                while time.time() - start_time < max_wait_time:
                    # Check if progress indicator is still visible
                    if not progress_indicator.is_visible():
                        logger.info(
                            "Progress indicator disappeared, conversion may be complete"
                        )
                        break

                    # Check if download/success element has appeared
                    download_element = page.query_selector(
                        "a:has-text('Download'), button:has-text('Download')"
                    )
                    if download_element:
                        logger.info("Download element appeared, conversion is complete")
                        break

                    # Wait before checking again
                    time.sleep(5)

                logger.info("Conversion progress monitoring completed")
            except Exception as wait_error:
                logger.warning(
                    f"Error while waiting for conversion to complete: {str(wait_error)}"
                )
        else:
            logger.info("No explicit progress indicator found, waiting fixed time")
            time.sleep(
                60
            )  # Wait a longer fixed amount of time if no progress indicator

        screenshot_path = take_screenshot(
            page, "conversion_complete", "youtube_converter"
        )
        test_result.add_step(
            TestStep(
                name="wait_for_conversion",
                status="success",
                screenshot_path=screenshot_path,
            )
        )
        logger.info("Conversion process wait completed")
    except Exception as e:
        logger.error(f"Error during conversion process: {str(e)}")
        test_result.add_step(
            TestStep(
                name="wait_for_conversion",
                status="error",
                error_message=str(e),
                screenshot_path=take_screenshot(
                    page, "conversion_error", "youtube_converter"
                ),
            )
        )
        raise

    # Step 7: Check for download availability - SCREENSHOT 3: Final state with download available
    try:
        logger.info("Checking for download availability")

        # Wait for any final page updates
        page.wait_for_load_state("networkidle", timeout=10000)
        time.sleep(3)

        # SCREENSHOT 3: Final state with download available
        screenshot_path = take_screenshot(page, "final_state", "youtube_converter")

        # Extract text using OCR and check for errors
        ocr_text = extract_text_from_image(screenshot_path)
        logger.info(f"OCR Text from final state screenshot: {ocr_text}")

        # Add OCR text to step metadata
        metadata = {"ocr_text": ocr_text}

        # Check for errors and download availability in OCR text using Groq
        final_result = groq_service.check_final_state(ocr_text)

        if final_result.get("error", False):
            error_message = final_result.get(
                "message", "Unknown error detected in OCR text"
            )
            logger.error(f"Error detected in final state: {error_message}")
            test_result.add_step(
                TestStep(
                    name="check_download_availability",
                    status="failure",
                    error_message=error_message,
                    screenshot_path=screenshot_path,
                    metadata=metadata,
                )
            )
            raise Exception(f"Conversion failed: {error_message}")

        download_available = final_result.get("download_available", False)

        # Perform manual check if Groq analysis didn't confirm download availability
        if not download_available:
            # Look for download button
            download_button_selectors = [
                "a:has-text('Download')",
                "button:has-text('Download')",
                ".download-button",
                "#download-button",
                "[data-action='download']",
                ".result-actions a",
                ".download-link",
            ]

            for selector in download_button_selectors:
                download_button = page.query_selector(selector)
                if download_button and download_button.is_visible():
                    download_available = True
                    logger.info(f"Download button found with selector: {selector}")
                    break

            # Check for success message if download button not found
            if not download_available:
                success_selectors = [
                    "div:has-text('Success')",
                    "div:has-text('Complete')",
                    "div:has-text('Ready')",
                    ".success-message",
                    ".complete-message",
                    ".conversion-complete",
                    ".result-ready",
                ]

                for selector in success_selectors:
                    success_message = page.query_selector(selector)
                    if success_message and success_message.is_visible():
                        download_available = True
                        logger.info(f"Success message found with selector: {selector}")
                        break

            # Check for errors
            error_selectors = [
                "div:has-text('Error')",
                "div:has-text('Failed')",
                ".error-message",
                ".conversion-error",
                ".alert-danger",
            ]

            for selector in error_selectors:
                error_message = page.query_selector(selector)
                if error_message and error_message.is_visible():
                    try:
                        error_text = error_message.inner_text()
                        logger.error(f"Conversion error found: {error_text}")
                        test_result.add_step(
                            TestStep(
                                name="check_download_availability",
                                status="failure",
                                error_message=error_text,
                                screenshot_path=screenshot_path,
                                metadata=metadata,
                            )
                        )
                        raise Exception(f"Conversion failed: {error_text}")
                    except Exception as error_extract_error:
                        logger.error(
                            f"Conversion error element found but couldn't extract text: {str(error_extract_error)}"
                        )
                        raise Exception("Conversion failed with unspecified error")

        if download_available:
            test_result.add_step(
                TestStep(
                    name="check_download_availability",
                    status="success",
                    screenshot_path=screenshot_path,
                    metadata=metadata,
                )
            )
            logger.info("Download is available, test successful")
        else:
            logger.warning("No clear download button or success message found")
            test_result.add_step(
                TestStep(
                    name="check_download_availability",
                    status="warning",
                    error_message="No clear download button or success message found",
                    screenshot_path=screenshot_path,
                    metadata=metadata,
                )
            )

        # Collect all OCR text from key screenshots for final analysis
        screenshots_ocr = {
            "initial": test_result.steps[0].metadata.get(
                "ocr_text", "No OCR text available"
            ),
            "before_conversion": metadata.get("ocr_text", "No OCR text available"),
            "final": metadata.get("ocr_text", "No OCR text available"),
        }

        # Request final AI analysis from Groq
        analysis_result = groq_service.analyze_test_full(screenshots_ocr)

        # Update test result with analysis
        test_result.analysis = analysis_result.get("analysis", "No analysis available")
        test_result.troubleshooting = analysis_result.get(
            "troubleshooting", "No troubleshooting recommendations available"
        )

    except Exception as e:
        if "Conversion failed" not in str(e):
            logger.error(f"Error checking download availability: {str(e)}")
            test_result.add_step(
                TestStep(
                    name="check_download_availability",
                    status="error",
                    error_message=str(e),
                    screenshot_path=take_screenshot(
                        page, "download_check_error", "youtube_converter"
                    ),
                )
            )
        raise
