FROM python:3.9-slim

WORKDIR /rag_multi_gemini

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Grant write permissions to the working directory
RUN chmod -R a+w /rag_multi_gemini

EXPOSE 8501

CMD ["streamlit", "run", "rag_multi_gemini.py", "--server.port=8501", "--server.address=0.0.0.0"]
