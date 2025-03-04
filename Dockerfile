FROM python:3.9-slim

# Install git to clone repository
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /rag_app

# Copy requirements first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Clone the entire repository to get txt_files
RUN git clone http://github.com/red-sat/Rag-application /tmp/repo

# Copy txt_files from the cloned repository
RUN mkdir -p /rag_app/txt_files && \
    cp /tmp/repo/txt_files/*.txt /rag_app/txt_files/ && \
    rm -rf /tmp/repo

# Copy the rest of the application
COPY . .

# Expose the Streamlit port
EXPOSE 8501

# Use a non-root user for security
RUN useradd -m appuser
USER appuser

# Command to run the application
CMD ["streamlit", "run", "rag_multi_gemini.py", "--server.port=8501", "--server.address=0.0.0.0"]
