FROM python:3.13-slim
WORKDIR /app
COPY traffic.py .
USER 1654
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "traffic.py"]
