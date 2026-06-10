# IT Help Desk Support Agent — container image.
#
# Build:  docker build -t it-helpdesk-agent .
# Run:    docker run -e ANTHROPIC_API_KEY=sk-ant-... -p 8501:8501 it-helpdesk-agent
#
# Note: the image is large (~3 GB) because it bundles PyTorch and the
# embedding model — normal for self-contained ML services.

FROM python:3.11-slim

WORKDIR /app

# Install dependencies first to leverage Docker layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model at build time so containers start
# instantly. Keep the name in sync with EMBEDDING_MODEL in src/config.py.
RUN python -c "from sentence_transformers import SentenceTransformer; \
SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

# Skip Streamlit's first-run interactive email prompt.
RUN mkdir -p /root/.streamlit \
    && printf '[general]\nemail = ""\n' > /root/.streamlit/credentials.toml

COPY src/ src/
COPY .streamlit/ .streamlit/

EXPOSE 8501

CMD ["python", "-m", "streamlit", "run", "src/app.py", \
     "--server.address=0.0.0.0", "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
