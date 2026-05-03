FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

RUN useradd -m -u 10002 appuser
WORKDIR /app

COPY runtime/browser/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY runtime/browser /app
COPY config /app/config

EXPOSE 8001
USER appuser
CMD ["python", "manage.py", "runserver", "0.0.0.0:8001"]
