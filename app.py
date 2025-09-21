# app.py
import os
import google.generativeai as genai
import cloudinary
import cloudinary.uploader
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
CORS(app)

# --- API Keys & Configuration ---
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# --- Helper Functions ---
# --- Helper Functions ---
def generate_product_description(product_name, keywords):
    """Generates product description, social media post, and hashtags using the Gemini API."""

    model = genai.GenerativeModel('gemini-2.5-pro')

    prompt = f"""
I will provide you with a product name and keywords. Your response MUST be formatted with '---' as the only delimiter between each section.

You are an expert copywriter for a local artisan marketplace. Your task is to write a compelling, SEO-optimized product description, a short social media post, and a list of hashtags for a handmade product.

Product Name: {product_name}
Keywords/Details: {keywords}

---
**Product Description:**
Write a detailed and engaging description of the product. Highlight its unique qualities, the materials used, and the story behind it.

---
**Social Media Post:**
Write a short, catchy post for Instagram or Facebook that encourages engagement.

---
**Hashtags:**
Generate 5-10 relevant and popular hashtags.
"""

    try:
        response = model.generate_content(prompt)

        if not hasattr(response, 'text') or not response.text:
            print("Gemini API returned an empty or invalid response.")
            return None

        full_text = response.text.strip()

        # Split the text into parts based on "---"
        parts = full_text.split('---')

        # Initialize defaults
        description_text = "Could not generate a full description."
        social_post_text = "Could not generate a social media post."
        hashtags_list = []

        # Attempt to parse each section safely
        if len(parts) > 0:
            for part in parts:
                if "**Product Description:**" in part:
                    description_text = part.replace('**Product Description:**', '').strip()
                elif "**Social Media Post:**" in part:
                    social_post_text = part.replace('**Social Media Post:**', '').strip()
                elif "**Hashtags:**" in part: # Changed from "**Hashtags:**:" to "**Hashtags:**"
                    hashtags_list = part.replace('**Hashtags:**', '').strip().split() # Removed colon from replace

        if not hashtags_list and "Hashtags:" in full_text:
            # Fallback if the split didn't catch hashtags (e.g., if it was the only part after last ---)
            hashtag_line = full_text.split("Hashtags:")[-1].strip()
            if hashtag_line:
                hashtags_list = hashtag_line.split()

        if not description_text and "Product Description:" in full_text:
             description_text = full_text.split("Product Description:")[-1].split("Social Media Post:")[0].strip() if "Social Media Post:" in full_text else full_text.split("Product Description:")[-1].strip()

        if not social_post_text and "Social Media Post:" in full_text:
            social_post_text = full_text.split("Social Media Post:")[-1].split("Hashtags:")[0].strip() if "Hashtags:" in full_text else full_text.split("Social Media Post:")[-1].strip()

        return {
            "description": description_text,
            "social_post": social_post_text,
            "hashtags": hashtags_list
        }
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return None

def upload_and_enhance_image(image_file):
    """Uploads an image to Cloudinary and applies an 'improve' effect."""
    try:
        upload_result = cloudinary.uploader.upload(
            image_file,
            folder="artisan-assistant",
            quality="auto",
            effect="improve"
        )
        return upload_result['secure_url']
    except Exception as e:
        print(f"Error uploading image to Cloudinary: {e}")
        return None

# --- Main API Endpoint ---
@app.route('/api/generate', methods=['POST'])
def generate_content():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    image_file = request.files['image']
    product_name = request.form.get('product_name', 'Handmade Product')
    keywords = request.form.get('keywords', 'unique, eco-friendly, made with love')

    # Step 1: Enhance Image
    enhanced_image_url = upload_and_enhance_image(image_file)
    if not enhanced_image_url:
        return jsonify({"error": "Failed to process image"}), 500

    # Step 2: Generate Text
    generated_text = generate_product_description(product_name, keywords)
    if not generated_text:
        return jsonify({"error": "Failed to generate content"}), 500

    # Step 3: Return combined response
    response_data = {
        "enhanced_image_url": enhanced_image_url,
        "generated_text": generated_text
    }
    return jsonify(response_data), 200

if __name__ == '__main__':
    app.run(debug=True)
