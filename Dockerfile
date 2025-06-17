# Gunakan image Python resmi
FROM python:3.10-slim

# Atur working directory
WORKDIR /app

# Salin file
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port streamlit
EXPOSE 8501

# Jalankan streamlit
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.enableCORS=false"]