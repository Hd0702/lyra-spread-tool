import telegram


class TelegramClient:
    def __init__(self, token: str, chat_id: str):
        self._bot = telegram.Bot(token=token)
        self._chat_id = chat_id

    """
    Sends a particular message to a telegram chat.
    At this time, the telegram bot has no way to determine which chats are active and which are not.
    Therefore, we cannot retrieve every chat that this bot is added to and assume it is safe to send a message.
    Unfortunately, we must tell the bot which chats it can use for now.
    """
    async def send_message(self, message: str) -> telegram.Message:
        return await self._bot.send_message(self._chat_id, message)
