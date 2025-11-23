from django.shortcuts import render
import os
import requests
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.conf import settings

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


# === Hugging Face API (Multimodal - LLaVA) ===
def send_to_huggingface(text, image_path=None):
    API_KEY = settings.HUGGINGFACE_API_KEY
    headers = {"Authorization": f"Bearer {API_KEY}"}

    if len(text) > MAX_CHARS_FOR_DEEPSEEK:
        text = text[:MAX_CHARS_FOR_DEEPSEEK] + "\n\n[Text truncated for AI processing]"

    # === CASE 1: Image Analysis (LLaVA) ===
    if image_path:
        # FIXED URL: Added /models/
        API_URL = "https://router.huggingface.co/models/llava-hf/llava-1.5-7b-hf"
        
        import base64
        with open(image_path, "rb") as img_file:
            b64_image = base64.b64encode(img_file.read()).decode('utf-8')
            
        # LLaVA prompt format
        prompt = f"USER: <image>\n{text if text else 'Describe this image in detail.'}\nASSISTANT:"
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 500,
                "images": [b64_image]
            }
        }
    
    # === CASE 2: Text Analysis (Zephyr) ===
    else:
        # FIXED URL: Switched to Zephyr and added /models/
        API_URL = "https://router.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta"
        
        # Zephyr/Mistral prompt format
        prompt = f"""<|system|>
You are an AI assistant that analyzes documents.
</s>
<|user|>
Document Content:
{text}

Task: Provide a concise summary and key insights from the document above.
</s>
<|assistant|>"""

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 500,
                "temperature": 0.5,
                "top_p": 0.9,
                "return_full_text": False
            }
        }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            return data[0]['generated_text'] if isinstance(data, list) else data.get('generated_text', '')
        else:
            return f"[AI Error: {response.status_code} - {response.text}]"
            
    except Exception as e:
        return f"[AI Request Failed: {str(e)}]"


# === Upload View (Multimodal) ===
@csrf_exempt
def upload_file(request):
    if request.method == "POST" and request.FILES.getlist("files"):
        files = request.FILES.getlist("files")
        all_responses = ""

        for file in files:
            file_path = default_storage.save(file.name, file)
            text = ""
            filename_lower = file.name.lower()
            is_image = False

            try:
                if filename_lower.endswith(".pdf"):
                    text = extract_text_from_pdf(file_path)
                elif filename_lower.endswith(".docx"):
                    text = extract_text_from_docx(file_path)
                elif filename_lower.endswith((".jpg", ".jpeg", ".png")):
                    is_image = True
                elif filename_lower.endswith(".txt"):
                    text = file.read().decode("utf-8")
                else:
                    all_responses += f"File: {file.name}\nError: Unsupported file type\n\n"
                    continue

                if not is_image and not text.strip():
                    all_responses += f"File: {file.name}\nError: No text extracted\n\n"
                    continue

                # Send to AI
                ai_response = send_to_huggingface(text, image_path=file_path if is_image else None)
                all_responses += f"File: {file.name}\nAI Analysis:\n{ai_response}\n\n"

            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

        return HttpResponse(all_responses.strip(), content_type="text/plain")

    return HttpResponse("Error: No files uploaded", content_type="text/plain")


# ============================================
# LUMORA AI PROXY VIEWS (Hugging Face)
# ============================================

class LumoraChatView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user_prompt = request.data.get('prompt')
        conversation_history = request.data.get('conversation_history', [])
        image_data = request.data.get('image')  # Base64 encoded image string
        
        if not user_prompt and not image_data:
            return Response(
                {"error": "Prompt or Image is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        API_KEY = settings.HUGGINGFACE_API_KEY
        headers = {"Authorization": f"Bearer {API_KEY}"}

        # === CASE 1: Image Present (Use LLaVA) ===
        if image_data:
            # FIXED URL: Added /models/
            API_URL = "https://router.huggingface.co/models/llava-hf/llava-1.5-7b-hf"
            
            prompt = f"USER: <image>\n{user_prompt if user_prompt else 'Describe this image.'}\nASSISTANT:"
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 500,
                    "images": [image_data]
                }
            }

        # === CASE 2: Text Only (Use Zephyr) ===
        else:
            # FIXED URL: Switched to Zephyr and ensure /models/ is present
            API_URL = "https://router.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta"
            
            system_prompt = """You are **Lumora**, the SKHOLAR AI Assistant for students of the **University of Benin (UNIBEN)**.
🎓 Personality & Role
- Friendly, supportive, and smart.
- Understands Nigerian Pidgin but replies in clear English.
💡 Capabilities
1. Academic help: explanations, problem-solving.
2. Campus info: verified data about UNIBEN.
⚖️ Rules
- Never invent information.
- Keep answers concise."""

            # Build prompt with Zephyr format <|system|>...<|user|>...
            prompt = f"<|system|>\n{system_prompt}</s>\n"
            
            for msg in conversation_history:
                role = "user" if msg['role'] == 'user' else "assistant"
                prompt += f"<|{role}|>\n{msg['text']}</s>\n"
            
            # Add current message
            prompt += f"<|user|>\n{user_prompt}</s>\n<|assistant|>"

            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 1000,
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "return_full_text": False
                }
            }

        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                generated_text = data[0]['generated_text'] if isinstance(data, list) else data.get('generated_text', '')
                return Response({"response": generated_text})
            else:
                return Response(
                    {"error": f"HF Error {response.status_code}: {response.text}"}, 
                    status=response.status_code
                )
                
        except Exception as e:
            return Response(
                {"error": f"Internal Server Error: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CbtExplanationView(APIView):
    """Proxy for CBT answer explanations"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        question = request.data.get('question')
        correct_answer = request.data.get('correct_answer')
        user_answer = request.data.get('user_answer')
        options = request.data.get('options', [])

        if not all([question, correct_answer, user_answer]):
            return Response(
                {"error": "Missing required fields"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        is_correct = user_answer.strip().lower() == correct_answer.strip().lower()
        
        # Zephyr format
        prompt = f"""<|system|>
You are a helpful tutor explaining CBT exam answers to university students.
</s>
<|user|>
Question: {question}
Correct Answer: {correct_answer}
Student's Answer: {user_answer}
{f"All Options: {', '.join(options)}" if options else ''}

Task: {'Explain why this answer is correct' if is_correct else "Explain why the student's answer is wrong and why the correct answer is right"}.
Keep it concise (under 100 words).
</s>
<|assistant|>"""

        # FIXED URL: Switched to Zephyr
        API_URL = "https://router.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta"
        API_KEY = settings.HUGGINGFACE_API_KEY
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 300,
                "temperature": 0.7,
                "return_full_text": False
            }
        }

        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                explanation = data[0]['generated_text'] if isinstance(data, list) else data.get('generated_text', '')
                return Response({"explanation": explanation})
            else:
                return Response({"error": response.text}, status=response.status_code)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PdfSummaryView(APIView):
    """Proxy for PDF summarization"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        text = request.data.get('text')
        max_length = request.data.get('max_length', 150)
        min_length = request.data.get('min_length', 50)

        if not text:
            return Response({"error": "Text is required"}, status=status.HTTP_400_BAD_REQUEST)

        # FIXED URL: Added /models/
        API_URL = "https://router.huggingface.co/models/facebook/bart-large-cnn"
        API_KEY = settings.HUGGINGFACE_API_KEY
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        payload = {
            "inputs": text.strip(),
            "parameters": {
                "max_length": max_length,
                "min_length": min_length,
                "do_sample": False
            }
        }

        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                summary = data[0]['summary_text'] if isinstance(data, list) else data.get('summary_text', '')
                return Response({"summary": summary})
            else:
                return Response({"error": response.text}, status=response.status_code)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)