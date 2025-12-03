# Use Python 3.10 slim
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    git \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements_fixed.txt .

# Install Python dependencies with specific order
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir \
    aiohttp>=3.9.3 \
    && pip install --no-cache-dir -r requirements_fixed.txt

# Copy application
COPY . .

# Create directories
RUN mkdir -p logs cache downloads

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application
CMD ["sh", "-c", "python bot.py"]
