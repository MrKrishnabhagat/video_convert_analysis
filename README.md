Agentic AI Backend for Automated File Conversion Testing
This project is an AI-powered backend application that automates the testing of a file conversion website (Video-Converter.com). It enables users to run predefined tests, view test results, and generate detailed reports on the performance, accuracy, and reliability of the file conversion service.

Features
✅ Automated Testing: Run automated tests against Video-Converter.com using Playwright
 ✅ AI-Powered Analysis: Use Groq API to analyze test results and generate troubleshooting suggestions
 ✅ Dynamic Script Generation: Generate test scripts dynamically based on specific test parameters
 ✅ Comprehensive Reporting: View test results, screenshots, and AI analysis in a user-friendly interface
 ✅ Test History: Track all test runs with detailed metrics and outcomes

Requirements
Python 3.8+
Playwright
Groq API key
Streamlit
Docker (optional)

Setup
Local Setup
Clone the repository:

 git clone https://github.com/MrKrishnabhagat/video_convert_analysis
cd video_convert_analysis


Create a virtual environment and install dependencies:

 python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt


Install Playwright browsers:

 playwright install


Create a .env file with your Groq API key:

 GROQ_API_KEY=your_groq_api_key_here


Run the application:

 streamlit run app.py


Docker Setup
Build the Docker image:

 docker build -t video-converter-testing .


Run the container:

 docker run -p 8501:8501 --env GROQ_API_KEY=your_groq_api_key_here video-converter-testing


Access the application at: http://localhost:8501



Usage
Open the application in your web browser.
Enter a YouTube URL to test.
Select the test type (Standard or AI-Generated).
Configure advanced options if needed.
Click "Run Test" to start the automated testing process.
View the test results, including:
Test summary
Step-by-step details
AI analysis and troubleshooting suggestions
Screenshots of each test step

Project Structure
project/
├── requirements.txt
├── config.py
├── app.py
├── utils/
│   ├── __init__.py
│   ├── screenshot.py
│   └── logger.py
├── services/
│   ├── __init__.py
│   ├── groq_service.py
│   └── playwright_service.py
├── models/
│   ├── __init__.py
│   └── test_result.py
└── tests/
    ├── __init__.py
    └── youtube_converter_test.py


Key Components
📌 app.py - Streamlit application interface
 📌 config.py - Configuration settings
 📌 services/groq_service.py - Groq API integration for LLM analysis
 📌 services/playwright_service.py - Playwright service for browser automation
 📌 tests/youtube_converter_test.py - Test implementation for YouTube video conversion
 📌 models/test_result.py - Data models for test results
 📌 utils/ - Utility functions for screenshots and logging

Contributing
Fork the repository
Create a feature branch
 git checkout -b feature/amazing-feature


Commit your changes
 git commit -m 'Add some amazing feature'


Push to the branch
 git push origin feature/amazing-feature


Open a Pull Request

License
This project is licensed under the MIT License - see the LICENSE file for details.

