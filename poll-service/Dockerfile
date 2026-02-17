FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files (new structure)
COPY main.py ./main.py
COPY config ./config
COPY controller ./controller
COPY service ./service
COPY repository ./repository
COPY model ./model

ENV PYTHONPATH=/app

EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
