from django.shortcuts import render
import os
import requests
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.conf import settings
import base64
from django.core.files.base import ContentFile

from PyPDF2 import PdfReader
from docx import Document
from PIL import Image
import pytesseract
from pdf2image import convert_from_path

# === Settings ===
MAX_CHARS_FOR_AI = 8000

# === Text Extractors ===
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
    try:
        return pytesseract.image_to_string(Image.open(file_path))
    except Exception as e:
        print(f"OCR failed (Tesseract may not be installed): {e}")
        return "[Image text extraction is not available on this server. Please manually describe what's in the image.]"


# ============================================
# GROQ API INTEGRATION
# ============================================

def query_groq(messages, model="llama-3.1-8b-instant", max_tokens=1000, temperature=0.7):
    """
    Call Groq API with chat completion format
    
    Args:
        messages: List of {"role": "user/assistant/system", "content": "text"}
        model: Groq model name
        max_tokens: Maximum response length
        temperature: Creativity level (0.0-1.0)
    
    Returns:
        str: AI response or error message
    """
    API_KEY = settings.GROQ_API_KEY
    
    if not API_KEY:
        return "[AI is currently unavailable - Configuration error]"
    
    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content'].strip()
        
        elif response.status_code == 429:
            return "[Rate limit reached - Please try again in a moment]"
        
        elif response.status_code == 401:
            return "[API authentication failed - Please contact support]"
        
        else:
            return f"[AI temporarily unavailable - Error {response.status_code}]"
            
    except requests.Timeout:
        return "[Request timeout - Please try again]"
    
    except Exception as e:
        return f"[AI service error: {str(e)}]"


# === Simple Fallback Summary (No AI) ===
def simple_summary(text, max_sentences=5):
    """Basic extractive summary - completely free"""
    sentences = text.replace('!', '.').replace('?', '.').split('.')
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    return '. '.join(sentences[:max_sentences]) + '.' if sentences else text[:500]


# ============================================
# FILE UPLOAD & ANALYSIS
# ============================================

@csrf_exempt
def upload_file(request):
    """Handle file uploads and extract/analyze content"""
    
    if request.method != "POST" or not request.FILES.getlist("files"):
        return HttpResponse("Error: No files uploaded", content_type="text/plain")
    
    files = request.FILES.getlist("files")
    all_responses = ""

    for file in files:
        file_path = default_storage.save(file.name, file)
        text = ""
        filename_lower = file.name.lower()

        try:
            # Extract text based on file type
            if filename_lower.endswith(".pdf"):
                text = extract_text_from_pdf(file_path)
            elif filename_lower.endswith(".docx"):
                text = extract_text_from_docx(file_path)
            elif filename_lower.endswith((".jpg", ".jpeg", ".png")):
                text = extract_text_from_image(file_path)
            elif filename_lower.endswith(".txt"):
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            else:
                all_responses += f"File: {file.name}\nError: Unsupported file type\n\n"
                continue

            if not text.strip():
                all_responses += f"File: {file.name}\nError: No text extracted\n\n"
                continue

            # Truncate if too long
            if len(text) > MAX_CHARS_FOR_AI:
                text = text[:MAX_CHARS_FOR_AI] + "\n\n[Text truncated...]"

            # Analyze with AI
            messages = [
                {
                    "role": "system",
                    "content": "You are an AI assistant that analyzes documents. Provide concise summaries and key insights."
                },
                {
                    "role": "user",
                    "content": f"Document Content:\n{text}\n\nTask: Provide a concise summary and 3-5 key insights."
                }
            ]
            
            ai_response = query_groq(messages, max_tokens=500)
            all_responses += f"📄 File: {file.name}\n\n{ai_response}\n\n{'='*50}\n\n"

        except Exception as e:
            all_responses += f"File: {file.name}\nError: {str(e)}\n\n"
        
        finally:
            # Clean up uploaded file
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass

    return HttpResponse(all_responses.strip(), content_type="text/plain")


# ============================================
# LUMORA AI CHAT
# ============================================

class LumoraChatView(APIView):
    """Main chat interface for Lumora AI Assistant"""
    
    permission_classes = [permissions.IsAuthenticated]

    def get_user_context(self, user):
        """Build personalized context string from user profile"""
        # Get user's display name (prefer first_name, fallback to username)
        name = user.first_name.strip() if user.first_name else user.username
        
        # Try to get additional profile info
        context_parts = [f"The user's name is {name}."]
        
        try:
            profile = user.userprofile
            if profile.faculty:
                context_parts.append(f"Faculty: {profile.faculty.name}")
            if profile.department:
                context_parts.append(f"Department: {profile.department.name}")
            if profile.level:
                context_parts.append(f"Level: {profile.level.name}")
        except Exception:
            pass  # No profile or error - just use name
        
        return " ".join(context_parts)

    def post(self, request):
        user_prompt = request.data.get('prompt')
        conversation_history = request.data.get('conversation_history', [])
        
        if not user_prompt:
            return Response(
                {"error": "Prompt is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get personalized user context
        user_context = self.get_user_context(request.user)

        # Handle File Attachment (PDF/Image)
        file_data = request.data.get('file_data')
        mime_type = request.data.get('mime_type')
        attached_text_context = ""

        if file_data and mime_type:
            try:
                import tempfile
                print(f"[AI File Upload] Received file_data length: {len(file_data)}, mime_type: {mime_type}")
                
                # Decode base64 - handle both "data:...;base64,XXX" format and raw base64
                if ';base64,' in file_data:
                    format, imgstr = file_data.split(';base64,')
                else:
                    imgstr = file_data
                    
                ext = mime_type.split('/')[-1]
                file_bytes = base64.b64decode(imgstr)
                
                # Use tempfile instead of default_storage (works with Cloudinary)
                with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as temp_file:
                    temp_file.write(file_bytes)
                    temp_path = temp_file.name
                
                print(f"[AI File Upload] Saved to temp: {temp_path}")

                # Extract text
                if 'pdf' in mime_type:
                    attached_text_context = extract_text_from_pdf(temp_path)
                    print(f"[AI File Upload] PDF extracted {len(attached_text_context)} chars")
                elif 'image' in mime_type:
                    attached_text_context = extract_text_from_image(temp_path)
                    print(f"[AI File Upload] Image OCR result: {len(attached_text_context)} chars")
                
                # Cleanup temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)

                if attached_text_context:
                    attached_text_context = f"\n\n[USER ATTACHED FILE CONTENT]:\n{attached_text_context[:MAX_CHARS_FOR_AI]}\n[END OF FILE CONTENT]\n"
            
            except Exception as e:
                print(f"[AI File Upload] Error processing file: {e}")
                import traceback
                traceback.print_exc()
                # Continue without the file content if error occurs

        # Build message context
        messages = [
            {
                "role": "system",
                "content": f'''You are **Lumora**, the SKHOLAR AI Assistant for students of the **University of Benin (UNIBEN)**.

👤 **Current User Context**
{user_context}
Use this information to personalize your responses. Address the user by their name naturally (e.g., "Hey [Name]!", "No wahala [Name]!", I got you!").

🎓 Personality
- You're like a brilliant, friendly senior student who's always got time to help.
- Warm, encouraging, and a bit witty - you make learning feel less stressful.
- You get Nigerian Pidgin and slang (e.g., "wetin", "abeg", "mi gee") - respond naturally!
- You celebrate wins ("You got this! 🔥") and comfort struggles ("No stress, let's break it down 💪").
- Keep things conversational and human - no robotic vibes!

💡 What You Can Do
1. **Academics**: Explain concepts, solve problems, summarize notes, prep for exams.
2. **Study Support**: Time management tips, motivation, study techniques.
3. **Campus Life**: Help with UNIBEN info, directions, student life advice.
4. **General Chat**: You can have casual conversations on any topic - just be helpful and friendly!

🚫 What You Can't Do (Yet!)
- You DON'T have access to real-time information (today's date, current news, live events).
- If asked about current events, dates, or live info, say something like: "I don't have access to live updates yet, but the team is working on adding that! 🚀 For now, you can check the Gist Updates section in the app."
- Never make up current events, news, or time-sensitive information.

⚖️ Core Rules
- Be accurate. If unsure, say so and suggest where to find reliable info.
- Keep answers clear and well-structured, but don't be boring about it!
- Use emojis naturally to express personality 🎯
- Don't force a tone, try to match the tone of the user's message.
- NEVER ASSUME ANYTHING TO PREVENT HALLUCINATION
- IF YOU FEEL YOURE TRAILING (HALLUCINATING) JUST SAY "I currently can't answer this question, but the problem solvers are working on it! 🚀"

🧑‍💻 About Your Creators
SKHOLAR was built with ❤️ by "The Problem Solvers" - a talented student team:
- Isreal Irene Idemudia - male (Team Lead & Backend)
- Oreoluwa Ifedinma Chiazor - male (Frontend & Software Engineer)
- Kingsley Ogedegbe - male (Python & Backend Engineer)
- Annabel Aigbe Akbar - female (Web Developer)
- Christabel Obianuju Ojekwu - female (UI/UX Designer)
- Stephanie Odilile Mordi - female (QA & Personnel Manager)

🧮 Math Formatting
- Use valid LaTeX for mathematical expressions.
- Inline math: Use $E=mc^2$ format
- Block math: Use $$x = \\frac{{-b \\pm \\sqrt{{b^2 - 4ac}}}}{{2a}}$$ format'''
            }
        ]
        
        # Add conversation history (limit to last 6 messages to save tokens)
        for msg in conversation_history[-6:]:
            role = msg.get('role', 'user')
            content = msg.get('text', '')
            if content:
                messages.append({
                    "role": role,
                    "content": content
                })
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": user_prompt + attached_text_context
        })
        
        # Get AI response
        result = query_groq(
            messages, 
            model="llama-3.1-8b-instant",  # Fast & efficient
            max_tokens=800,
            temperature=0.7
        )
        
        # Handle errors
        if result.startswith("["):
            return Response(
                    {"error": result}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response({"response": result})


# ============================================
# CBT EXPLANATION
# ============================================

class CbtExplanationView(APIView):
    """Explain CBT exam answers to students"""
    
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        question = request.data.get('question')
        correct_answer = request.data.get('correct_answer')
        user_answer = request.data.get('user_answer')
        options = request.data.get('options', [])

        if not all([question, correct_answer, user_answer]):
            return Response(
                {"error": "Missing required fields (question, correct_answer, user_answer)"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        is_correct = user_answer.strip().lower() == correct_answer.strip().lower()
        
        # Build explanation prompt
        options_text = f"\nOptions: {', '.join(options)}" if options else ""
        
        task = (
            "Explain why this answer is correct and what concept it demonstrates."
            if is_correct else
            "Explain why the student's answer is incorrect and why the correct answer is right."
        )
        
        messages = [
            {
                "role": "system",
                "content": "You are a patient tutor explaining exam answers to university students. Be clear, concise (under 100 words), and educational."
            },
            {
                "role": "user",
                "content": f"""Question: {question}{options_text}

Correct Answer: {correct_answer}
Student's Answer: {user_answer}

{task}"""
            }
        ]
        
        result = query_groq(
            messages,
            model="llama-3.1-8b-instant",
            max_tokens=250,
            temperature=0.6  # Lower temperature for more focused explanations
        )
        
        # Fallback for errors
        if result.startswith("["):
            if is_correct:
                result = f"✓ Correct! The answer is '{correct_answer}'. Well done!"
            else:
                result = f"✗ Incorrect. The correct answer is '{correct_answer}', not '{user_answer}'. Please review this topic."
        
        return Response({"explanation": result})


# ============================================
# PDF SUMMARIZATION
# ============================================

class PdfSummaryView(APIView):
    """Summarize document text"""
    
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        text = request.data.get('text')
        max_length = request.data.get('max_length', 200)
        use_ai = request.data.get('use_ai', True)

        if not text:
            return Response(
                {"error": "Text is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Option 1: Simple summary (free, no AI)
        if not use_ai:
            summary = simple_summary(text, max_sentences=5)
            return Response({
                "summary": summary,
                "method": "extractive"
            })
        
        # Option 2: AI summary
        if len(text) > MAX_CHARS_FOR_AI:
            text = text[:MAX_CHARS_FOR_AI] + "\n[Text truncated...]"

        messages = [
            {
                "role": "system",
                "content": "You are an expert at summarizing academic documents. Provide clear, concise summaries that capture key points."
            },
            {
                "role": "user",
                "content": f"Summarize this document in approximately {max_length} words:\n\n{text}"
            }
        ]
        
        result = query_groq(
            messages,
            model="llama-3.1-8b-instant",
            max_tokens=400,
            temperature=0.5
        )
        
        if result.startswith("["):
            # Fallback to simple summary
            result = simple_summary(text, max_sentences=5)
            method = "extractive (fallback)"
        else:
            method = "ai"
        
        return Response({
            "summary": result,
            "method": method
        })