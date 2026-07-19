FROM python:3.14-alpine

RUN adduser -D -h /app exporter
WORKDIR /app

COPY exporter.py .

USER exporter
EXPOSE 9222

CMD ["python3", "exporter.py"]
