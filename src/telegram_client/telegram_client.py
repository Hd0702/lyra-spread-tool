import os

import telegram


class TelegramClient:
    def __init__(self, token: str = os.getenv("TELEGRAM_KEY")):
        self._bot = telegram.Bot(token=token)

    """
    Sends a particular message to a telegram chat.
    At this time, the telegram bot has no way to determine which chats are active and which are not.
    Therefore, we cannot retrieve every chat that this bot is added to and assume it is safe to send a message.
    Unfortunately, we must tell the bot which chats it can use for now.
    """

    async def send_message(self, message: str, chat_id: int = -1002075187090) -> telegram.Message:
        return await self._bot.send_message(chat_id, message)
