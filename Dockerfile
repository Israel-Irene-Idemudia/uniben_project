# Dockerfile for Skholar Django Backend
# Enables Tesseract OCR for image text extraction

FROM python:3.11-slim

# Install system dependencies including Tesseract OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Expose port (Render provides PORT env variable)
EXPOSE 8000

# Run with gunicorn
CMD gunicorn uniben_portal.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120
