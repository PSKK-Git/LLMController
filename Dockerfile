FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY migrations ./migrations
COPY alembic.ini .

ENV PYTHONPATH=/app/src
EXPOSE 8000

# Run DB migrations, then start the API.
CMD ["sh", "-c", "alembic upgrade head && uvicorn llmcontroller.main:app --host 0.0.0.0 --port 8000 --app-dir src"]
