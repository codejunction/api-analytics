FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . ./server
EXPOSE 3000
CMD ["uvicorn", "server.api.main:app", "--host", "0.0.0.0", "--port", "3000"]
