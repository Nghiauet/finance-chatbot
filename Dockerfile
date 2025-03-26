FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and setup files
COPY requirements.txt setup.py ./

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy the source code
COPY src/ ./src/

# Create necessary directories
RUN mkdir -p data/uploads data/raw_pdf data/converted_file logs

# Copy .env file
COPY .env ./.env
EXPOSE 8010
# Command to run the application
CMD ["python", "-m", "src.main", "--host", "0.0.0.0", "--port", "8010"]
