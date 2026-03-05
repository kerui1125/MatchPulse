# Multi-stage build for smaller final image
# Stage 1: Build stage with all dependencies
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies needed for Playwright and Python packages
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium only to save space)
RUN playwright install chromium && \
    playwright install-deps chromium

# Stage 2: Runtime stage (smaller final image)
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy Playwright browsers from builder
COPY --from=builder /root/.cache/ms-playwright /root/.cache/ms-playwright

# Copy application code
COPY src/ ./src/
COPY dashboard/ ./dashboard/

# Note: data/ directory is NOT copied (contains user's resume and embeddings)
# It will be created at runtime or mounted as volume

# Note: .env is NOT copied (it's in .gitignore)
# Environment variables should be set via:
# - Docker run: --env-file .env
# - Docker compose: environment section
# - GitHub Actions: secrets

# Create directories for runtime data
RUN mkdir -p /app/data/embeddings /app/data/resumes

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright

# Default command: run the pipeline
CMD ["python", "src/main.py", "--threshold", "0.78", "--top-k", "7"]
