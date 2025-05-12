FROM python:3.11-slim

WORKDIR /app

COPY wait-for-it.sh ./wait-for-it.sh
COPY alembic.ini .
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN chmod +x wait-for-it.sh

COPY app ./app
COPY alembic ./alembic

CMD ["/app/wait-for-it.sh", "db:5432", "--", "sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
