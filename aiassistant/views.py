from django.shortcuts import render
import os
import requests
from django.http import JsonResponse
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
    """Extract text from PDF. Fallback to OCR if no embedded text."""
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception as e:
        text += f"[Error reading PDF: {e}]\n"

    # OCR fallback for scanned PDFs
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

    # Trim text if too long
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
        return response.json()
    except Exception as e:
        return {"error": f"DeepSeek API error: {str(e)}"}


# === Upload View (Multiple Files) ===
@csrf_exempt
def upload_file(request):
    if request.method == "POST" and request.FILES.getlist("files"):
        files = request.FILES.getlist("files")
        all_responses = []

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
                    all_responses.append({"file": file.name, "error": "Unsupported file type"})
                    continue

                if not text.strip():
                    all_responses.append({"file": file.name, "error": "No text extracted"})
                    continue

                # Send to DeepSeek
                ai_response = send_to_deepseek(text)
                all_responses.append({"file": file.name, "ai_response": ai_response})

            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

        return JsonResponse(all_responses, safe=False)

    return JsonResponse({"error": "No files uploaded"}, status=400)
