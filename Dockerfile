FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 5000
CMD gunicorn app:app --bind 0.0.0.0:$PORT --log-level debug
