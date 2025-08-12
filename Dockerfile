FROM python:3.10-slim

WORKDIR /app

COPY /app/main.py .

CMD ["python", "main.py"]