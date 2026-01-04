
# Use official Playwright Python image (includes browsers and dependencies)
# This is much more stable than installing deps on slim Debian
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Set work directory
WORKDIR /app

# (No need to apt-get install dependencies, they are in the image)

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Cloud Run sets PORT env var, default 8080)
EXPOSE 8080

# Command to run the application
CMD exec uvicorn api.price_service:app --host 0.0.0.0 --port ${PORT}
