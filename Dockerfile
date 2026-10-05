FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg curl build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY j.py .

EXPOSE 8080

CMD ["python", "j.py"]
