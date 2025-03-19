# Dockerfile
FROM python:3.13-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN mkdir /app
ADD . /app
WORKDIR /app

RUN uv sync --frozen
CMD ["uv", "run", "vicareub2.py"]
