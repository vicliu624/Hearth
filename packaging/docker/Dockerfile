FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1             HEARTH_CONFIG=/data/hearth.toml

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src

RUN python -m pip install --upgrade pip &&             pip install .

EXPOSE 8480
VOLUME ["/data"]

CMD ["hearth-api"]
