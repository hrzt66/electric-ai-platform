FROM python:3.12-slim
WORKDIR /app
COPY python-ai-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY python-ai-service /app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090"]
