import groq
import os
import json
import re
from config import GROQ_API_KEY, GROQ_MODEL
from models.test_result import TestResult


class GroqService:
    def __init__(self):
        self.client = groq.Client(api_key=os.getenv("GROQ_API_KEY"))
        self.model = GROQ_MODEL

    def check_screenshot_for_errors(self, ocr_text, context=""):
        """
        Check OCR text for error messages and return structured error information

        Args:
            ocr_text: Text extracted from OCR
            context: Additional context about the screenshot

        Returns:
            Dictionary with error information
        """
        prompt = f"""
        Analyze this OCR text from a screenshot{' of ' + context if context else ''} and determine if there are any error messages or failures.
        
        Important: Ignore non-ASCII characters or special symbols that appear due to OCR processing. Only flag an error if clear error text like "error", "failed", "cannot", etc. is present with high confidence.
        
        You must respond with valid JSON in exactly this format, with NO additional text:
        
        Example 1 (no error):
        {{
            "error": false
        }}
        
        Example 2 (error found):
        {{
            "error": true,
            "message": "description of the error"
        }}
        
        OCR Text:
        {ocr_text}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=150,
            )

            error_analysis = response.choices[0].message.content.strip()

            # Try to extract just the JSON part if there's any extra text
            json_match = re.search(r"(\{.*\})", error_analysis, re.DOTALL)
            if json_match:
                error_analysis = json_match.group(1)

            return json.loads(error_analysis)
        except json.JSONDecodeError as e:
            return {
                "error": True,
                "message": f"Failed to parse LLM response as JSON: {str(e)}. Raw response: {error_analysis}",
            }
        except Exception as e:
            return {"error": True, "message": f"Error analyzing OCR text: {str(e)}"}

    def check_for_errors(self, ocr_text, context=""):
        """
        Check OCR text for error messages using Groq LLM

        Args:
            ocr_text: Text extracted from OCR
            context: Additional context about the screenshot

        Returns:
            Dictionary with error information
        """
        prompt = f"""
        Analyze this OCR text from a screenshot{' of ' + context if context else ''} and determine if there are any error messages or failures.
        
        You must respond with valid JSON in exactly this format:
        {{
            "error": false
        }}
        
        Or if there is an error:
        {{
            "error": true,
            "message": "description of the error"
        }}
        
        Do not include any explanations or additional text outside of the JSON structure.
        
        Here's the OCR text:
        {ocr_text}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=150,
            )

            error_analysis = response.choices[0].message.content

            # Try to extract just the JSON part if there's any extra text
            json_match = re.search(r"(\{.*\})", error_analysis, re.DOTALL)
            if json_match:
                error_analysis = json_match.group(1)

            return json.loads(error_analysis)
        except json.JSONDecodeError as e:
            return {
                "error": True,
                "message": f"Failed to parse LLM response as JSON: {str(e)}. Raw response: {error_analysis}",
            }
        except Exception as e:
            return {"error": True, "message": f"Error analyzing OCR text: {str(e)}"}

    def check_final_state(self, ocr_text):
        """
        Check final state OCR text to determine if download is available

        Args:
            ocr_text: Text extracted from final state screenshot

        Returns:
            Dictionary with error and download availability information
        """
        prompt = f"""
        Analyze this OCR text from the final screenshot of a YouTube video conversion process.
        Look for error messages, failure notifications, or any indications that the process failed.
        Also check if there are download links available or success messages indicating completion.
        
        You must respond with valid JSON in exactly this format, with NO additional text:
        
        Example 1 (no error, download available):
        {{
            "error": false,
            "download_available": true
        }}
        
        Example 2 (error found):
        {{
            "error": true,
            "message": "description of the error"
        }}
        
        Example 3 (no error, no download available):
        {{
            "error": false,
            "download_available": false
        }}
        
        OCR Text:
        {ocr_text}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200,
            )

            analysis = response.choices[0].message.content

            # Try to extract just the JSON part if there's any extra text
            json_match = re.search(r"(\{.*\})", analysis, re.DOTALL)
            if json_match:
                analysis = json_match.group(1)

            return json.loads(analysis)
        except json.JSONDecodeError as e:
            return {
                "error": True,
                "message": f"Failed to parse LLM response as JSON: {str(e)}. Raw response: {analysis}",
            }
        except Exception as e:
            return {"error": True, "message": f"Error analyzing final state: {str(e)}"}

    def analyze_test_full(self, screenshots_ocr):
        """
        Provide comprehensive analysis of a test based on multiple screenshots

        Args:
            screenshots_ocr: Dictionary mapping screenshot stages to OCR text

        Returns:
            Dictionary with analysis and troubleshooting
        """
        prompt = f"""
        Provide a comprehensive analysis of this YouTube video conversion test based on the OCR text from key screenshots.
        
        Screenshot 1 (Initial Navigation):
        {screenshots_ocr.get('initial', 'No OCR text available')}
        
        Screenshot 2 (Before Conversion):
        {screenshots_ocr.get('before_conversion', 'No OCR text available')}
        
        Screenshot 3 (Final State):
        {screenshots_ocr.get('final', 'No OCR text available')}
        
        You must respond with valid JSON in exactly this format, with NO additional text:
        
        {{
            "analysis": "detailed explanation of what happened during the test",
            "troubleshooting": "recommendations for addressing any issues found"
        }}
        
        If the test appears successful, note that in your analysis and provide any relevant observations.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1024,
            )

            analysis = response.choices[0].message.content

            # Try to extract just the JSON part if there's any extra text
            json_match = re.search(r"(\{.*\})", analysis, re.DOTALL)
            if json_match:
                analysis = json_match.group(1)

            return json.loads(analysis)
        except json.JSONDecodeError as e:
            return {
                "analysis": f"Error during analysis: Failed to parse LLM response as JSON: {str(e)}",
                "troubleshooting": "Check the logs for the raw LLM response and refine the prompt to ensure valid JSON output.",
            }
        except Exception as e:
            return {
                "analysis": f"Error during analysis: {str(e)}",
                "troubleshooting": "Please check the logs for more information.",
            }

    def analyze_screenshots(self, screenshot_data):
        """
        Use Groq LLM to analyze OCR text from screenshots and generate a comprehensive analysis

        Args:
            screenshot_data: List of dictionaries with keys 'step', 'screenshot_path', and 'ocr_text'

        Returns:
            Dictionary with 'analysis' and 'troubleshooting' keys
        """
        # Format the prompt for analysis, focusing only on the screenshots
        analysis_prompt = f"""
        You are an expert AI assistant analyzing screenshots from a YouTube video conversion website test.
        
        Screenshots with OCR text extracted:
        {json.dumps(screenshot_data, indent=2)}
        
        Based solely on the OCR text from the screenshots:
        1. Determine if any errors were detected in the interface
        2. Analyze what happened during the test
        3. Assess if the conversion process was working correctly
        4. Identify at which point, if any, the process failed
        
        You must respond with valid JSON in exactly this format, with NO additional text:
        
        {{
            "analysis": "your detailed analysis here",
            "troubleshooting": "your troubleshooting recommendations here"
        }}
        """

        try:
            # Call the Groq API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0.2,
                max_tokens=1024,
            )

            # Extract and parse the response
            llm_response = response.choices[0].message.content

            # Try to extract just the JSON part if there's any extra text
            json_match = re.search(r"(\{.*\})", llm_response, re.DOTALL)
            if json_match:
                llm_response = json_match.group(1)

            parsed_response = json.loads(llm_response)

            return {
                "analysis": parsed_response.get("analysis", "No analysis available"),
                "troubleshooting": parsed_response.get(
                    "troubleshooting", "No troubleshooting recommendations available"
                ),
            }
        except json.JSONDecodeError as e:
            return {
                "analysis": f"Error during screenshot analysis: Failed to parse LLM response as JSON: {str(e)}",
                "troubleshooting": "Check the raw LLM response in logs and refine the prompt to ensure valid JSON output.",
            }
        except Exception as e:
            return {
                "analysis": f"Error during screenshot analysis: {str(e)}",
                "troubleshooting": "Please check the logs for more information.",
            }

    def analyze_test_results(self, test_result: TestResult) -> TestResult:
        """
        Use Groq LLM to analyze test results, focusing only on screenshot OCR analysis

        Args:
            test_result: TestResult object containing test data

        Returns:
            Updated TestResult object with analysis and troubleshooting
        """
        # Extract OCR text from screenshots
        screenshot_data = []

        for step in test_result.steps:
            if step.metadata and "ocr_text" in step.metadata:
                screenshot_data.append(
                    {
                        "step": step.name,
                        "screenshot_path": step.screenshot_path,
                        "ocr_text": step.metadata["ocr_text"],
                    }
                )

        # If no screenshot data is available, return early
        if not screenshot_data:
            test_result.analysis = "No screenshot OCR data available for analysis"
            test_result.troubleshooting = "Ensure OCR is performed on screenshots"
            return test_result

        # Get analysis based only on screenshot data
        analysis_result = self.analyze_screenshots(screenshot_data)

        # Update the test result with the analysis
        test_result.analysis = analysis_result["analysis"]
        test_result.troubleshooting = analysis_result["troubleshooting"]

        return test_result
