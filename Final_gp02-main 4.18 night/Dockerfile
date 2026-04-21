FROM python:3.11-slim

# Unbuffered stdout/stderr so HF Space container logs show uvicorn/Python traces immediately.
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# Reduce CPU thread oversubscription / memory spikes on small HF Spaces CPU tiers.
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV NUMEXPR_NUM_THREADS=1
ENV TOKENIZERS_PARALLELISM=false

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-hf.txt ./

# CPU-only PyTorch to keep image lean (no CUDA needed for HF Spaces CPU runtime)
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir \
        torch \
        --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements-hf.txt

COPY . .

RUN chmod +x /app/scripts/hf_space_entrypoint.sh

# Weights: repo tracks kronos-small + tokenizer-base; optional empty dir for runtime downloads
RUN mkdir -p /app/kronos_weights

EXPOSE 8000

# Entrypoint prints startup lines + verifies `import api.main` so HF logs are not empty on import failure.
CMD ["/app/scripts/hf_space_entrypoint.sh"]
