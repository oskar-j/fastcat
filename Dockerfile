# Development image for fastcat. Pair it with the Redis container defined in
# docker-compose.yml:
#
#   docker compose up -d redis     # just a dockerized Redis on localhost:6379
#   docker compose run --rm fastcat pytest
#
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependency metadata first, so edits to the sources do not invalidate the
# layer that installs them.
COPY pyproject.toml README.md LICENSE.txt ./
COPY src ./src
RUN pip install --no-cache-dir --editable '.[dev]'

COPY tests ./tests
COPY sample.py ./

# Reach the Redis service by its compose hostname rather than localhost.
ENV FASTCAT_REDIS_HOST=redis \
    FASTCAT_REDIS_PORT=6379

CMD ["pytest"]
