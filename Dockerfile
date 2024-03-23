FROM python:3.11

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TELEGRAM_KEY=put-your-bot-here

RUN pip install --upgrade pip
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY . /app
WORKDIR /app/src

CMD ["python", "./main.py", "--expiry_date", "20240329", "--delta", ".03", "--depth", "20", "--spread_limit", ".03"]
