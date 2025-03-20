import streamlit as st
import os
import time
import pandas as pd
from datetime import datetime
from PIL import Image
import logging
import glob

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

# Initialize session state variables
if "test_results" not in st.session_state:
    st.session_state.test_results = []
if "current_test_result" not in st.session_state:
    st.session_state.current_test_result = None
if "log_path" not in st.session_state:
    st.session_state.log_path = None
if "test_in_progress" not in st.session_state:
    st.session_state.test_in_progress = False
if "selected_test_index" not in st.session_state:
    st.session_state.selected_test_index = 0


# Function to find all video files
def find_video_files():
    video_files = glob.glob(os.path.join(VIDEO_RECORDINGS_DIR, "*.webm"))
    return sorted(video_files, key=os.path.getmtime, reverse=True)


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

# Advanced options
with st.sidebar.expander("Advanced Options"):
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

# Check and display existing videos in sidebar
all_videos = find_video_files()
if all_videos:
    st.sidebar.divider()
    st.sidebar.subheader("Available Video Recordings")
    video_options = [os.path.basename(v) for v in all_videos]
    selected_video = st.sidebar.selectbox("Select a video to view", video_options)
    if st.sidebar.button("View Selected Video"):
        video_path = os.path.join(VIDEO_RECORDINGS_DIR, selected_video)
        st.sidebar.video(video_path, start_time=0)

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

                # Run the test
                with st.status("Running test...") as status:
                    st.write(f"Testing YouTube URL: {youtube_url}")
                    if record_video:
                        st.write("Recording video of the test execution")

                    # Execute the standard test
                    with PlaywrightService(
                        record_video=record_video,
                        headless=headless_mode,
                    ) as playwright_service:
                        test_result, log_path = playwright_service.execute_test(
                            run_standard_youtube_conversion_test,
                            youtube_url,
                            "youtube_converter",
                        )

                        # Ensure video path exists after test completion
                        if record_video and hasattr(test_result, "video_path"):
                            # Check if video file exists
                            if test_result.video_path and os.path.exists(
                                test_result.video_path
                            ):
                                st.write(
                                    f"Video recorded: {os.path.basename(test_result.video_path)}"
                                )
                            else:
                                # Try to find the latest video in the directory
                                latest_videos = find_video_files()
                                if latest_videos:
                                    test_result.video_path = latest_videos[0]
                                    st.write(
                                        f"Using latest video: {os.path.basename(test_result.video_path)}"
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

        # Quick access to video recording if available
        if (
            hasattr(test_result, "video_path")
            and test_result.video_path
            and os.path.exists(test_result.video_path)
        ):
            st.subheader("Quick Video Access")
            st.video(test_result.video_path)

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

        # Find videos from the current test and all available videos
        current_video = None
        if (
            hasattr(test_result, "video_path")
            and test_result.video_path
            and os.path.exists(test_result.video_path)
        ):
            current_video = test_result.video_path

        available_videos = find_video_files()

        # If no current video but videos are available, use the most recent one
        if not current_video and available_videos:
            current_video = available_videos[0]
            # Update the test result with this video path
            test_result.video_path = current_video
            st.session_state.current_test_result = test_result

        # Display current video if available
        if current_video:
            # Create container with border for video display
            video_container = st.container()
            with video_container:
                st.subheader(f"Test Recording: {os.path.basename(current_video)}")

                # Video player with fullscreen option
                st.video(current_video)

                # Video information
                video_size = os.path.getsize(current_video) / (1024 * 1024)  # MB
                video_modified = datetime.fromtimestamp(os.path.getmtime(current_video))

                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Video Size:** {video_size:.2f} MB")
                    st.write(f"**Created:** {video_modified}")

                with col2:
                    st.download_button(
                        "📥 Download Video",
                        data=open(current_video, "rb"),
                        file_name=os.path.basename(current_video),
                        mime="video/webm",
                        key="download_current_video",
                    )
        else:
            # No video available - offer to browse all videos
            st.warning("No video recording available for this test")
            st.write("This could be because:")
            st.write("- Video recording was disabled during test execution")
            st.write("- The test did not complete successfully")
            st.write("- The video file was moved or deleted")

            # Show all available videos if any exist
            if available_videos:
                st.subheader("Other Available Videos")
                st.write("You can view one of these previously recorded videos:")

                # Create a selection for available videos
                video_names = [os.path.basename(v) for v in available_videos]
                selected_video_name = st.selectbox("Select a video", video_names)
                selected_video_path = os.path.join(
                    VIDEO_RECORDINGS_DIR, selected_video_name
                )

                if st.button("View Selected Video"):
                    st.video(selected_video_path)
                    st.download_button(
                        "📥 Download Selected Video",
                        data=open(selected_video_path, "rb"),
                        file_name=selected_video_name,
                        mime="video/webm",
                        key="download_selected_video",
                    )
            else:
                st.info("No video recordings found in the videos directory")
                st.write(
                    "Try running a new test with 'Record test video' enabled in Advanced Options"
                )

# History section - modified to work without ButtonColumn
with st.expander("Test History"):
    if st.session_state.test_results:
        # Create a dataframe for test history
        history_data = []
        for i, result in enumerate(st.session_state.test_results):
            # Check if video exists
            has_video = (
                hasattr(result, "video_path")
                and result.video_path
                and os.path.exists(result.video_path)
            )

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
                    "Video": "✅" if has_video else "❌",
                }
            )

        # Create the dataframe
        history_df = pd.DataFrame(history_data)

        # Display the dataframe
        st.dataframe(
            history_df,
            column_config={
                "Video": st.column_config.TextColumn("Video Available"),
            },
            hide_index=True,
            use_container_width=True,
        )

        # Add a separate selection for viewing tests
        selected_test_number = st.selectbox(
            "Select a test to view:",
            options=range(1, len(st.session_state.test_results) + 1),
            format_func=lambda x: f"Test #{x}",
        )

        if st.button("View Selected Test"):
            # Set the selected test (adjust index because test numbers start at 1)
            selected_index = selected_test_number - 1
            st.session_state.selected_test_index = selected_index
            selected_test = st.session_state.test_results[selected_index]
            st.session_state.current_test_result = selected_test
            st.rerun()

        # Button to clear history
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
