FROM python:3.11-slim

WORKDIR /app

ENV BAA_HOST=0.0.0.0
ENV AGENT_PORT=5001
ENV BAA_DATA_DIR=/data
ENV BAA_SKIP_DEPENDENCY_CHECK=1

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python scripts/generate_demo_data.py

EXPOSE 5001
CMD ["python", "app.py"]
