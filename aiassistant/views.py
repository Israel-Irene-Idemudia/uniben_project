from django.shortcuts import render
import os
import requests
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage

from PyPDF2 import PdfReader
from docx import Document
from PIL import Image
import pytesseract
from pdf2image import convert_from_path

# === Settings ===
MAX_CHARS_FOR_DEEPSEEK = 5000  # trim large text for AI processing

# === Extractors ===
def extract_text_from_pdf(file_path):
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception as e:
        text += f"[Error reading PDF: {e}]\n"

    if not text.strip():
        try:
            images = convert_from_path(file_path)
            for img in images:
                text += pytesseract.image_to_string(img) + "\n"
        except Exception as e:
            text += f"[Error OCR scanned PDF: {e}]\n"

    return text.strip()


def extract_text_from_docx(file_path):
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])


def extract_text_from_image(file_path):
    return pytesseract.image_to_string(Image.open(file_path))


# === DeepSeek API ===
def send_to_deepseek(text):
    API_URL = "https://api.deepseek.com/v1/chat/completions"
    API_KEY = "PUT_YOUR_DEEPSEEK_API_KEY_HERE"

    if len(text) > MAX_CHARS_FOR_DEEPSEEK:
        text = text[:MAX_CHARS_FOR_DEEPSEEK] + "\n\n[Text truncated for AI processing]"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": text}
        ]
    }
    try:
        response = requests.post(API_URL, headers=headers, json=data)
        response.raise_for_status()
        # Assuming the AI response is a string in the JSON
        return response.json().get("ai_response", "[No response from AI]")
    except Exception as e:
        return f"[DeepSeek API error: {str(e)}]"


# === Upload View (Plain Text) ===
@csrf_exempt
def upload_file(request):
    if request.method == "POST" and request.FILES.getlist("files"):
        files = request.FILES.getlist("files")
        all_responses = ""

        for file in files:
            file_path = default_storage.save(file.name, file)
            text = ""
            filename_lower = file.name.lower()

            try:
                if filename_lower.endswith(".pdf"):
                    text = extract_text_from_pdf(file_path)
                elif filename_lower.endswith(".docx"):
                    text = extract_text_from_docx(file_path)
                elif filename_lower.endswith((".jpg", ".jpeg", ".png")):
                    text = extract_text_from_image(file_path)
                elif filename_lower.endswith(".txt"):
                    text = file.read().decode("utf-8")
                else:
                    all_responses += f"File: {file.name}\nError: Unsupported file type\n\n"
                    continue

                if not text.strip():
                    all_responses += f"File: {file.name}\nError: No text extracted\n\n"
                    continue

                ai_response = send_to_deepseek(text)
                all_responses += f"File: {file.name}\nAI Response:\n{ai_response}\n\n"

            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

        return HttpResponse(all_responses.strip(), content_type="text/plain")

    return HttpResponse("Error: No files uploaded", content_type="text/plain")
