# Use official Python Alpine image
FROM python:3.11-alpine

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TEMP_DOWNLOADS=/app/temp_downloads

# Install required system packages
RUN apk add --no-cache \
    build-base \
    libffi-dev \
    openssl-dev \
    ffmpeg

# Install required Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create app directory
WORKDIR /app

# Copy application files
COPY app.py .
COPY templates ./templates

# Create temp downloads directory
RUN mkdir -p ${TEMP_DOWNLOADS}

# Expose port
EXPOSE 5000

# Start the application
CMD ["python", "app.py"]