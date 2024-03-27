FROM python:3.10

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --upgrade pip

WORKDIR /usr/src/app

COPY . /usr/src/app

RUN pip install poetry
RUN poetry config virtualenvs.create false
RUN poetry install

EXPOSE 80
ENTRYPOINT ["poetry", "run", "main"]
CMD [ \
  "--expiry_date", "20240329", \
  "--delta", ".1", \
  "--depth", "20", \
  "--spread_limit", ".07", \
  "--telegram_key", "put-your-bot-here", \
  "--telegram_chat_id", "-1001956002222" \
]