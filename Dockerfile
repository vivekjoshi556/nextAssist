FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY .env /app/.env
COPY src /app/src
COPY app.py /app/app.py
COPY poetry.lock /app/poetry.lock
COPY pyproject.toml /app/pyproject.toml

RUN pip install --no-cache-dir poetry

RUN poetry config virtualenvs.create false

RUN poetry install --no-root --no-interaction --no-ansi

EXPOSE 8501

CMD ["streamlit", "run", "app.py"]
