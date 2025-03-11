from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
from openai import OpenAI
import base64
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import json
from dotenv import load_dotenv
import os
import re
from gevent.pywsgi import WSGIServer

load_dotenv()
# OpenRouter API settings
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_API_URL = os.getenv('OPENROUTER_API_URL')


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, allow_headers=["Content-Type", "Authorization"])


def encode_image_to_base64(image_path):
    """Encode an image file to a base64-encoded string."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")
    
def html_to_image(url, output_path="./screenshot.jpeg"):
    """Convert a webpage to an image using Playwright."""
    with sync_playwright() as p:
        browser =  p.chromium.launch(headless=True)
        context = browser.new_context()
        
        # Create a new page in the isolated context
        page = context.new_page()
        
        # Navigate to the URL
        page.goto(url)
        
        # Take a full-page screenshot
        page.screenshot(path=output_path, full_page=True)
        
        # Close the context and browser
        context.close()
        browser.close()

def scrape_html(url):
    """Scrape and return the HTML code from the given URL, excluding JavaScript and CSS."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup.find_all('script'):
            script.decompose()
        for style in soup.find_all('style'):
            style.decompose()
        for tag in soup.find_all(style=True):
            del tag['style']
        for link in soup.find_all('link', rel='stylesheet'):
            link.decompose()
        return soup.prettify()
    except requests.exceptions.RequestException as e:
        return f"Error fetching the URL: {str(e)}"


def collect_security_headers(url):
    """Collect security headers from the webpage."""
    response = requests.get(url)
    headers = response.headers

    # Extract relevant security headers , collect only necessary headers
    security_headers = {
        "X-XSS-Protection": headers.get("X-XSS-Protection"),
        "X-Frame-Options": headers.get("X-Frame-Options"),
        "Strict-Transport-Security": headers.get("Strict-Transport-Security"),
        "Content-Security-Policy": headers.get("Content-Security-Policy"),
        "X-Content-Type-Options": headers.get("X-Content-Type-Options"),
        "Referrer-Policy": headers.get("Referrer-Policy"),
        "Permissions-Policy": headers.get("Permissions-Policy"),
        "Cross-Origin-Resource-Policy": headers.get("Cross-Origin-Resource-Policy"),
        "Cross-Origin-Embedder-Policy": headers.get("Cross-Origin-Embedder-Policy"),
        "Cross-Origin-Opener-Policy": headers.get("Cross-Origin-Opener-Policy")
    }

    return security_headers


def query_openrouter(prompt , model, base64_image = None):
    """Query the OpenRouter API to evaluate the frontend."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt,
                        }
                    ]
                }
        ]
    if (base64_image is not None):
        messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt,
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
        ]

    payload = {
        "model": model, 
        "messages": messages
    }
    # Prepare the messages for the API request
        
    response = requests.post(OPENROUTER_API_URL, headers=headers, data=json.dumps(payload))
    return response.json()

def extract_information(generated_text):
    """
    Extract score and evaluation from a string.
    """
    # Extract the score
    score_match = re.search(r"\*\*Score\*\*:\s*([\d.]+)/5", generated_text)
    score = float(score_match.group(1)) if score_match else None

    # Extract the evaluation
    evaluation_match = re.search(r"\*\*Evaluation\*\*:\s*(.*?)(?=\s*\*\*Suggestions\*\*:|\Z)", generated_text, re.DOTALL)
    evaluation = evaluation_match.group(1).strip() if evaluation_match else None

    return score, evaluation

def get_evaluation(prompt,  model , image_path = None,):
    
    """Evaluate the frontend HTML for issues and provide a score out of 5."""
    # Refined prompt for better results
    try :
        base64_image = None
        if (image_path):
            base64_image = encode_image_to_base64(image_path)
        openrouter_response = query_openrouter(prompt, model, base64_image)
        if "choices" in openrouter_response and len(openrouter_response["choices"]) > 0:
            # Extract the generated text
            generated_text = openrouter_response["choices"][0]["message"]["content"]
            if "</think>" in generated_text:
                # Split the text at </think> and take the part after it
                generated_text = generated_text.split("</think>")[1].strip()
            score, evaluation = extract_information (generated_text)
            # Return a JSON object with the score and evaluation
            if score is not None and evaluation is not None:
                    return json.dumps({
                        "score": score,
                        "evaluation": evaluation
                    }, indent=2)
            else:
                    return json.dumps({
                        "error": "Unable to extract score or evaluation from the response."
                    }, indent=2)
        
        else:
            return "Error: Unable to analyze the HTML."
    except Exception as e:
        # Handle any errors that occur during the process
        return f"An error occurred: {str(e)}"
    

@app.route('/evaluate_security', methods=['POST'])
def evaluate_security():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        # Step 1: Scrape HTML
        security_metrics = collect_security_headers(url)
        prompt = f"""
        Analyze the following security metrics and evaluate the quality of the page on a scale of 1 to 5, where 1 is poor and 5 is excellent. Focus on the following key security aspects:
        1. **HTTPS Usage**: Is the page served over HTTPS? (Score higher if HTTPS is properly implemented.
        2. **Security Headers**: Are critical security headers present and correctly configured?
        3. **Vulnerability to Common Attacks**: Is the page protected against common vulnerabilities like:


        Provide:
        1. A score out of 5 for overall overall security quality of the page.
        2. A list of the most critical issues, if any.

        Format your response as:
        - **Score**: [Score]/5
        - **Evaluation**: [Detailed evaluation]
        - **Suggestions**: [Suggestions for improvement]

        Keep your response concise in maximum of 200 words but ensure all aspects are covered.
       
        Security metrics:
        {security_metrics}
        """
        model = "deepseek/deepseek-chat:free"
        # Step 2: Query DeepSeek
        response = get_evaluation(prompt, model)
        print("securityresponse", response)
        return response
    except Exception as e:
        return str(e)

@app.route('/evaluate_html', methods=['POST'])
def evaluate_html():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "URL is required"}), 400
    try:
        # Step 1: Scrape HTML
        html_elements = scrape_html(url)
        # Step 2: Query DeepSeek
        prompt = f"""
        Analyze the following HTML code and evaluate its quality on a scale of 1 to 5, where 1 is poor and 5 is excellent. Provide a list of selected issues and suggestions for improvement. Focus on:
        1. Missing or invalid attributes (e.g., `alt`, `aria-label`, buttons without `type` or `onclick`).
        2. Semantic HTML issues (e.g., misuse of `<div>` instead of `<button>`).
        3. Coherence and structure of the code (e.g., logical structure, readability).
        4. HTML bugs

        After analyzing the HTML, provide **only the following**:
        1. A score out of 5 for overall quality of the HTM.
        2. A list of the most critical issues, if any.

        Format your response as:
        - **Score**: [Score]/5
        - **Evaluation**: [Detailed evaluation]
        - **Suggestions**: [Suggestions for improvement]

        Keep your response concise in maximum of 200 words but ensure all aspects are covered.

        HTML Code:
        {html_elements}
        """
        model = "deepseek/deepseek-chat:free"
        response = get_evaluation(prompt, model)
        print("htmlresponse", response)
        # Step 3: Return Evaluation
        return response
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/take_screenshot', methods=['POST'])
def take_screenshot():
    data = request.json
    print(data  )
    url = data.get('url')
    print("url", url  )
    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        output_path = "./screenshot.jpeg"
        html_to_image(url, output_path)

        # Return a success response with the path to the screenshot
        return jsonify({
            "status": "success",
            "message": "Screenshot taken successfully",
            "screenshot_path": output_path
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500




@app.route('/evaluate_user_experience', methods=['POST'])
def evaluate_user_experience():
    data = request.json
    print(data  )
    url = data.get('url')
    print("url", url  )
    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        
        prompt = """
        Analyze the user experience (UX) of this webpage and provide a score out of 5 (1 = poor, 5 = excellent). Evaluate the following aspects:

        1. **Visual Design**:
            - Color scheme: Is it appealing and consistent?
            - Typography: Are fonts readable and appropriately sized?
            - Spacing: Is there adequate whitespace and padding?

        2. **Layout and Organization**:
            - Clarity: Is the content easy to understand?
            - Hierarchy: Is there a clear visual hierarchy (e.g., headings, subheadings)?
            - Alignment: Are elements properly aligned?

        3. **Accessibility**:
            - Contrast: Is there sufficient contrast between text and background?
            - Readability: Is text easy to read?

        4. **Style**:
            - Efficiency: Is the design balanced (not too simple or overly complex)?

        Provide:
        1. A score out of 5 for overall UX quality.
        2. A detailed evaluation of strengths and weaknesses.
        3. Suggestions for improvement.

        Format your response as:
        - **Score**: [Score]/5
        - **Evaluation**: [Detailed evaluation]
        - **Suggestions**: [Suggestions for improvement]

        Keep your response concise in maximum of 200 words but ensure all aspects are covered.
        """
        img_path = "./screenshot.jpeg"
        model = "google/gemini-2.0-flash-lite-preview-02-05:free"
        response = get_evaluation(prompt,  model, img_path)
        print("user_experience_response", response)
        return response
    except Exception as e:
        return str(e)

        
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug = True)
