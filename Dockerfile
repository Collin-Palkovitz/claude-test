# Runs anywhere a container runs — laptop today, any $5 VPS or scheduled
# cloud job later. State lives in /app/data (mount it) and secrets come from
# the environment, so moving hosts is: copy the data dir, set the env vars.
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
VOLUME /app/data

ENTRYPOINT ["python", "-m", "src.main"]
CMD ["signals"]
