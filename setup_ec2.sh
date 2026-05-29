#!/bin/bash
# EC2 Setup Script for Skholar Backend
# Designed for Ubuntu 22.04 LTS / 24.04 LTS

set -e

echo "Starting EC2 Infrastructure Setup for Skholar..."

# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install system dependencies (including Tesseract OCR from Dockerfile)
sudo apt-get install -y python3-pip python3-venv python3-dev libpq-dev postgresql-client nginx curl tesseract-ocr tesseract-ocr-eng gcc

# Create project directory
PROJECT_DIR="/var/www/skholar"
sudo mkdir -p $PROJECT_DIR
sudo chown -R ubuntu:ubuntu $PROJECT_DIR

echo "=========================================="
echo "Infrastructure dependencies installed."
echo "Please clone or copy your code to $PROJECT_DIR"
echo "=========================================="

echo "Creating Gunicorn systemd service template..."
sudo bash -c "cat > /etc/systemd/system/skholar.service <<EOF
[Unit]
Description=gunicorn daemon for Skholar
Requires=skholar.socket
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/var/www/skholar
ExecStart=/var/www/skholar/venv/bin/gunicorn \\
          --access-logfile - \\
          --workers 3 \\
          --bind unix:/run/skholar.sock \\
          uniben_portal.wsgi:application

[Install]
WantedBy=multi-user.target
EOF"

sudo bash -c "cat > /etc/systemd/system/skholar.socket <<EOF
[Unit]
Description=gunicorn socket for Skholar

[Socket]
ListenStream=/run/skholar.sock

[Install]
WantedBy=sockets.target
EOF"

echo "Creating Nginx configuration template..."
sudo bash -c "cat > /etc/nginx/sites-available/skholar <<EOF
server {
    listen 80;
    server_name api.skholar.site;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        alias /var/www/skholar/staticfiles/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/skholar.sock;
    }
}
EOF"

echo "Setup script created! To finalize installation after code is synced, run:"
echo "sudo ln -sf /etc/nginx/sites-available/skholar /etc/nginx/sites-enabled/"
echo "sudo systemctl daemon-reload"
echo "sudo systemctl enable skholar.socket skholar.service"
echo "sudo systemctl restart nginx"
