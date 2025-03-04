FROM python:3.9-slim

# Set working directory
WORKDIR /rag_multi_gemini

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create a directory for text files
RUN mkdir -p /rag_multi_gemini/txt_files

# Expose the Streamlit port
EXPOSE 8501

# Use a non-root user for security
RUN useradd -m appuser
USER appuser

# Command to run the application
CMD ["streamlit", "run", "rag_multi_gemini.py", "--server.port=8501", "--server.address=0.0.0.0"]
