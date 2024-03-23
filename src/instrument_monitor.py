import json
import logging
import time
from typing import Dict, List

import telegram
import websockets

from lyra.constants import LYRA_WEBSOCKET_URI
from lyra.subscription_listener import SubscriptionListener
from telegram_client.telegram_client import TelegramClient
logger = logging.getLogger(__name__)


class InstrumentMonitor:
    def __init__(self, instruments: List[Dict], spread_limit: float, depth: float, delta: float, telegram_client: TelegramClient = None):
        if not instruments:
            raise ValueError("Instruments cannot be empty")
        self._instruments = instruments
        self._spread_limit = spread_limit
        self._depth = depth
        self._delta = delta
        if telegram_client is None:
            telegram_client = TelegramClient()
        self._telegram_client = telegram_client

    async def start_monitor(self):
        ws_client = await websockets.connect(LYRA_WEBSOCKET_URI)
        listener = SubscriptionListener([instrument["instrument_name"] for instrument in self._instruments])
        try:
            await listener.create_subscription_task()
            current_epoch_milli = int(time.time() * 1000)
            while current_epoch_milli < self._instruments[0]["scheduled_deactivation"] * 1000:
                instruments_to_check = await self._get_instrument_names_within_delta(ws_client)
                instruments_to_alert = await self._determine_instruments_outside_spread(ws_client, listener, instruments_to_check)
                current_epoch_milli = int(time.time() * 1000)
                if instruments_to_alert:
                    await self._send_messages_to_telegram(instruments_to_alert)
            logger.info("Expired date has hit. Closing connections.")
        finally:
            await ws_client.close()
            await listener.close()

    async def _determine_instruments_outside_spread(self, ws, listener: SubscriptionListener, instrument_names: List[str]):
        last_valid_spreads = {instrument: int(time.time() * 1000) for instrument in instrument_names}
        instruments_to_alert = {}
        current_epoch_milli = int(time.time() * 1000)
        five_minutes_from_now_milli = current_epoch_milli + 300000
        while current_epoch_milli < five_minutes_from_now_milli:
            current_ticker = await self._get_ticker(ws, instrument_names[0])
            spot_price = float(current_ticker["result"]["index_price"])
            for instrument_name in instrument_names:
                subscription_message = await listener.get_message(instrument_name)
                bids = subscription_message["params"]["data"]["bids"]
                asks = subscription_message["params"]["data"]["asks"]
                difference = (self._calculate_depth_price(asks) - self._calculate_depth_price(bids)) / spot_price
                if difference >= self._spread_limit:
                    logger.info(f"Spread is too high: {difference} for instrument {instrument_name}")
                    if subscription_message["params"]["data"]["timestamp"] - last_valid_spreads[instrument_name] >= 60000:
                        last_valid_spreads[instrument_name] = subscription_message["params"]["data"]["timestamp"]
                        logger.info(f"Spread has been too high for {instrument_name} for over 60 seconds")
                        instruments_to_alert[instrument_name] = difference
                else:
                    logger.debug(f"valid pass for {instrument_name}")
                    last_valid_spreads[instrument_name] = subscription_message["params"]["data"]["timestamp"]
                current_epoch_milli = int(time.time() * 1000)
        return instruments_to_alert

    async def _get_instrument_names_within_delta(self, ws) -> List[str]:
        instruments_within_delta = []
        for instrument in self._instruments:
            instrument_name = instrument["instrument_name"]
            ticker = await self._get_ticker(ws, instrument_name)
            instrument_delta = float(ticker["result"]["option_pricing"]["delta"])
            if 0 + self._delta <= abs(instrument_delta) <= 1 - self._delta:
                logger.debug(f"instrument is within delta 0 or 1: {instrument_delta} for instrument {instrument_name}")
                instruments_within_delta.append(instrument_name)
        return instruments_within_delta

    async def _send_messages_to_telegram(self, instruments_to_alert: Dict[str, float]) -> telegram.Message:
        message = f"""
        Alert! Within the last 5 minutes the following instruments had a spread greater than the limit {self._spread_limit * 100}% for at least 1 minute.

        Here are the instruments and their spreads:
        """ + "\n".join(
            [f"{instrument}: {spread * 100}%" for instrument, spread in instruments_to_alert.items()]
        )
        left_aligned_message = "\n".join([line.strip() for line in message.splitlines()])
        logger.debug("Sending messages to telegram")
        return await self._telegram_client.send_message(left_aligned_message)

    async def _get_ticker(self, ws, instrument_name: str) -> Dict:
        ticker_message = {"id": "99", "method": "public/get_ticker", "params": {"instrument_name": instrument_name}}
        ticker_response = await self._make_call(ws, ticker_message)
        return ticker_response

    async def _make_call(self, ws, message) -> Dict:
        await ws.send(json.dumps(message))
        response = json.loads(await ws.recv())
        if "error" in response:
            raise ValueError(f"Error in response {response}")
        return response

    """
    This function assumes that the orders are already sorted by price.
    For bids, the orders are sorted in descending order by price (first index)
    For asks, the orders are sorted in ascending order by price.
    The second entry in each order is the volume of the underlying.
    """
    def _calculate_depth_price(self, orders: List[List[str]]) -> float:
        # first entry is the price second is the amount of ETH
        depth_left = self._depth / 2
        total_price = 0
        for order in orders:
            price, volume = float(order[0]), float(order[1])
            if volume >= depth_left:
                total_price += price * depth_left
            else:
                total_price += price * volume
                depth_left -= volume
        return total_price / self._depth / 2
