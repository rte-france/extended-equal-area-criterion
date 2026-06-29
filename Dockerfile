FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /opt/deeac

RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

COPY setup.py README.md ./
COPY deeac ./deeac

RUN pip install --upgrade pip \
    && pip install . \
    && python -c "from deeac.main import deeac; print('deeac import ok')"

WORKDIR /work

ENTRYPOINT ["deeac"]
CMD ["--help"]
