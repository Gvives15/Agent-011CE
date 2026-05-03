FROM python:3.11-slim

RUN useradd -m -u 10001 appuser
WORKDIR /app

COPY runtime/agent/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY runtime/agent /app
COPY config /app/config

ENV PYTHONUNBUFFERED=1
ENV OPEN_PEAK_CONFIG_DIR=/app/config
EXPOSE 8000

USER appuser
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
