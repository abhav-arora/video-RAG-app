FROM python:3.9-slim

# Install git
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CHANGE 1: Just copy the file directly (we are already in the folder)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CHANGE 2: Copy everything in the current folder
COPY . .

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]