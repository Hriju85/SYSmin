FROM python:3.11-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends procps gcc python3-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir .

EXPOSE 8742

ENV HOST=0.0.0.0
ENV PORT=8742

CMD ["throttleros", "--host", "0.0.0.0", "--port", "8742", "--no-browser"]
