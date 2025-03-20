import streamlit as st
import os
import time
import importlib
import pandas as pd
from datetime import datetime
from PIL import Image
import logging

from config import SCREENSHOTS_DIR, VIDEO_RECORDINGS_DIR
from services.playwright_service import PlaywrightService
from services.groq_service import GroqService
from models.test_result import TestResult
from tests.youtube_converter_test import run_standard_youtube_conversion_test
from utils.ocr import extract_text_from_image

# Set up page configuration
st.set_page_config(
    page_title="Video Converter Testing Agent",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state variables f
if "test_results" not in st.session_state:
    st.session_state.test_results = []
if "current_test_result" not in st.session_state:
    st.session_state.current_test_result = None
if "log_path" not in st.session_state:
    st.session_state.log_path = None
if "test_in_progress" not in st.session_state:
    st.session_state.test_in_progress = False

# Title and description
st.title("🎥 Video Converter Testing Agent")
st.markdown(
    """
This application automates testing of the Video-Converter.com website using AI-powered analysis.
Upload a YouTube URL and run automated tests to verify conversion functionality with OCR text extraction.
"""
)

# Sidebar
st.sidebar.header("Test Configuration")

# YouTube URL input
youtube_url = st.sidebar.text_input(
    "YouTube URL",
    value="https://www.youtube.com/watch?v=aWk2XZ_8IhA",
    help="Enter the YouTube URL to test for conversion",
)

# Test selection
test_type = st.sidebar.selectbox(
    "Test Type",
    ["Standard YouTube Conversion Test", "AI-Generated Test Script"],
    help="Select the type of test to run",
)

# Advanced options
with st.sidebar.expander("Advanced Options"):
    use_dynamic_script = st.checkbox(
        "Use AI to generate test script",
        value=False,
        help="Generate a custom test script using Groq LLM",
    )
    headless_mode = st.checkbox(
        "Run in headless mode",
        value=True,
        help="Run browser in headless mode (no visible UI)",
    )
    record_video = st.checkbox(
        "Record test video",
        value=True,
        help="Record a video of the test execution",
    )

# Run test button
if st.sidebar.button(
    "Run Test", type="primary", disabled=st.session_state.test_in_progress
):
    if not youtube_url or not youtube_url.startswith("http"):
        st.error("Please enter a valid YouTube URL")
    else:
        # Start test process
        st.session_state.test_in_progress = True

        with st.spinner("Running test..."):
            # Create progress bar
            progress_bar = st.progress(0)

            try:
                groq_service = GroqService()
                progress_bar.progress(10)

                # Generate dynamic script if requested
                dynamic_script = None
                if use_dynamic_script or test_type == "AI-Generated Test Script":
                    with st.status("Generating test script with AI..."):
                        st.write("Asking Groq LLM to generate a custom test script...")
                        dynamic_script = groq_service.generate_playwright_script(
                            youtube_url
                        )
                        st.write("Script generated successfully!")

                        # Create function from the generated script
                        exec_globals = {}
                        exec_globals.update(globals())
                        exec(dynamic_script, exec_globals)
                        ai_test_func = exec_globals.get("run_youtube_conversion_test")

                progress_bar.progress(30)

                # Run the test
                with st.status("Running test...") as status:
                    st.write(f"Testing YouTube URL: {youtube_url}")
                    if record_video:
                        st.write("Recording video of the test execution")

                    # Choose which test to run
                    test_func = run_standard_youtube_conversion_test
                    if use_dynamic_script or test_type == "AI-Generated Test Script":
                        if ai_test_func:
                            test_func = ai_test_func
                            st.write("Using AI-generated test script")
                        else:
                            st.warning(
                                "AI-generated script failed, falling back to standard test"
                            )

                    # Execute the test with video recording if enabled
                    with PlaywrightService(
                        record_video=record_video,
                        headless=headless_mode,
                    ) as playwright_service:
                        test_result, log_path = playwright_service.execute_test(
                            test_func, youtube_url, "youtube_converter"
                        )

                        # Store results and log path
                        st.session_state.current_test_result = test_result
                        st.session_state.log_path = log_path
                        st.session_state.test_results.append(test_result)

                    st.write(
                        f"Test completed with status: {test_result.overall_status}"
                    )
                    status.update(label="Test completed!", state="complete")

                progress_bar.progress(70)

                # Analyze the results with Groq LLM
                with st.status("Analyzing results with AI..."):
                    st.write(
                        "Asking Groq LLM to analyze the test results and OCR text..."
                    )
                    analyzed_result = groq_service.analyze_test_results(test_result)
                    st.session_state.current_test_result = analyzed_result
                    st.write("Analysis complete!")

                progress_bar.progress(100)

                # Update the UI to show results
                st.success("Test and analysis completed successfully!")

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                logging.exception("Error during test execution")
            finally:
                # Reset the progress flag
                st.session_state.test_in_progress = False

                # Force page refresh to show results
                st.rerun()

# Display test results if available
if st.session_state.current_test_result:
    test_result = st.session_state.current_test_result

    # Create tabs for different sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "Test Summary",
            "Step Details",
            "AI Analysis",
            "Screenshots & OCR",
            "Video Recording",
        ]
    )

    with tab1:
        # Test summary
        st.header("Test Summary")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Test Status", test_result.overall_status.upper())

        with col2:
            if test_result.end_time and test_result.start_time:
                duration = (
                    test_result.end_time - test_result.start_time
                ).total_seconds()
                st.metric("Duration", f"{duration:.2f} seconds")

        with col3:
            success_steps = sum(
                1 for step in test_result.steps if step.status == "success"
            )
            total_steps = len(test_result.steps)
            st.metric("Success Rate", f"{success_steps}/{total_steps}")

        # Test details
        st.subheader("Test Details")
        details_cols = st.columns(2)

        with details_cols[0]:
            st.write(f"**YouTube URL:** {test_result.youtube_url}")
            st.write(f"**Start Time:** {test_result.start_time}")
            if st.session_state.log_path:
                st.download_button(
                    label="Download Log File",
                    data=open(st.session_state.log_path, "rb"),
                    file_name=os.path.basename(st.session_state.log_path),
                    mime="text/plain",
                    key="download_log_file",
                )

        with details_cols[1]:
            st.write(f"**Test Name:** {test_result.test_name}")
            st.write(f"**End Time:** {test_result.end_time}")

            # Generate report button
            if st.button("Generate Full Report", key="generate_report_button"):
                st.download_button(
                    label="Download Report",
                    data=pd.DataFrame([test_result.to_dict()]).to_csv(index=False),
                    file_name=f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key="download_report",
                )

    with tab2:
        # Step details
        st.header("Test Steps")

        # Create a dataframe for steps
        steps_data = []
        for i, step in enumerate(test_result.steps):
            steps_data.append(
                {
                    "Step #": i + 1,
                    "Name": step.name,
                    "Status": step.status.upper(),
                    "Timestamp": step.timestamp,
                    "Error": step.error_message or "None",
                }
            )

        if steps_data:
            steps_df = pd.DataFrame(steps_data)
            st.dataframe(
                steps_df,
                column_config={
                    "Status": st.column_config.TextColumn(
                        "Status", help="Result status of this step", width="small"
                    )
                },
                use_container_width=True,
            )
        else:
            st.info("No test steps recorded")

    with tab3:
        # AI Analysis
        st.header("AI Analysis")

        if test_result.analysis:
            st.subheader("What Happened")
            st.write(test_result.analysis)

            st.subheader("Troubleshooting")
            st.write(test_result.troubleshooting)
        else:
            st.info("No AI analysis available for this test")

    with tab4:
        # Screenshots and OCR
        st.header("Screenshots & OCR Text")

        # Find screenshots for this test
        screenshots = []
        for step in test_result.steps:
            if step.screenshot_path and os.path.exists(step.screenshot_path):
                # Get OCR text if available
                ocr_text = "No OCR text available"
                if step.metadata and "ocr_text" in step.metadata:
                    ocr_text = step.metadata["ocr_text"]

                screenshots.append((step.name, step.screenshot_path, ocr_text))

        if screenshots:
            # Display screenshots with OCR text
            for i, (name, path, ocr_text) in enumerate(screenshots):
                st.subheader(f"{i+1}. {name.replace('_', ' ').title()}")

                # Create columns for screenshot and OCR text
                col1, col2 = st.columns([1, 1])

                with col1:
                    st.image(path, caption=f"Screenshot: {name}", use_column_width=True)
                    st.download_button(
                        f"Download Screenshot",
                        data=open(path, "rb"),
                        file_name=os.path.basename(path),
                        mime="image/png",
                        key=f"download_screenshot_{i}",
                    )

                with col2:
                    st.subheader("Extracted Text (OCR)")
                    st.text_area("", value=ocr_text, height=300, key=f"ocr_{i}")

                st.divider()
        else:
            st.info("No screenshots available for this test")

    with tab5:
        # Video Recording
        st.header("Test Video Recording")

        if test_result.video_path and os.path.exists(test_result.video_path):
            st.video(test_result.video_path)
            st.download_button(
                "Download Test Video Recording",
                data=open(test_result.video_path, "rb"),
                file_name=os.path.basename(test_result.video_path),
                mime="video/webm",
                key="download_test_video",
            )
        else:
            st.info(
                "No video recording available for this test. Make sure to enable video recording in the Advanced Options."
            )

# History section
with st.expander("Test History"):
    if st.session_state.test_results:
        # Create a dataframe for test history
        history_data = []
        for i, result in enumerate(st.session_state.test_results):
            history_data.append(
                {
                    "Test #": i + 1,
                    "YouTube URL": result.youtube_url,
                    "Status": result.overall_status.upper(),
                    "Start Time": result.start_time,
                    "End Time": result.end_time,
                    "Duration": (
                        f"{(result.end_time - result.start_time).total_seconds():.2f}s"
                        if result.end_time
                        else "N/A"
                    ),
                    "Video": (
                        "Available"
                        if result.video_path and os.path.exists(result.video_path)
                        else "Not Available"
                    ),
                }
            )

        history_df = pd.DataFrame(history_data)
        st.dataframe(history_df, use_container_width=True)

        if st.button("Clear History", key="clear_history_button"):
            st.session_state.test_results = []
            st.session_state.current_test_result = None
            st.rerun()
    else:
        st.info("No test history available")

# Footer
st.markdown("---")
st.markdown(
    """
**Video Converter Testing Agent** | Powered by Playwright, Groq LLM, OCR, and Streamlit
"""
)
