FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
RUN useradd --create-home astral && mkdir /app/runtime && chown astral:astral /app/runtime
USER astral
EXPOSE 8766
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8766", "--workers", "1", "--timeout-graceful-shutdown", "5"]
