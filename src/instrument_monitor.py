import json
import logging
import time
from datetime import datetime
from typing import Dict, List

import telegram
import websockets

import utils.black76
from lyra.constants import LYRA_WEBSOCKET_URI
from lyra.subscription_listener import SubscriptionListener
from src.utils import depth_calculator
from telegram_client.telegram_client import TelegramClient

logger = logging.getLogger(__name__)


class InstrumentMonitor:
    _seconds_to_millis_multiplier = 1000

    def __init__(self, instruments: List[Dict], spread_limit: float, depth: float, delta: float, telegram_client: TelegramClient):
        if not instruments:
            raise ValueError("Instruments cannot be empty")
        self._instruments = instruments
        self._spread_limit = spread_limit
        # dividing by 2 since we only care about depth on one side (bid or asks). They'll both sum up to depth * 2 ideally.
        self._depth = depth / 2
        self._delta = delta
        self._telegram_client = telegram_client

    async def start_monitor(self):
        ws_client = await websockets.connect(LYRA_WEBSOCKET_URI)
        listener = SubscriptionListener([instrument["instrument_name"] for instrument in self._instruments])
        try:
            await listener.create_subscription_task()
            current_epoch_milli = int(time.time() * self._seconds_to_millis_multiplier)
            expiry = self._instruments[0]["option_details"]["expiry"]
            while current_epoch_milli < expiry * self._seconds_to_millis_multiplier:
                instruments_to_check = await self._get_instrument_names_within_delta(ws_client)
                instruments_to_alert = await self._determine_instruments_outside_spread(ws_client, listener, instruments_to_check)
                current_epoch_milli = int(time.time() * self._seconds_to_millis_multiplier)
                if instruments_to_alert:
                    await self._send_messages_to_telegram(instruments_to_alert)
            logger.info("Expired date has hit. Closing connections.")
        finally:
            await ws_client.close()
            await listener.close()

    async def _determine_instruments_outside_spread(self, ws, listener: SubscriptionListener, instruments: List[Dict]) -> Dict[str, str]:
        last_valid_spreads = {instrument["instrument_name"]: int(time.time() * self._seconds_to_millis_multiplier) for instrument in instruments}
        last_valid_liquidity_spreads = last_valid_spreads.copy()
        low_spread_alerts = {}
        low_liquidity_alerts = {}
        sixty_seconds_in_millis = 60000
        current_epoch_milli = int(time.time() * self._seconds_to_millis_multiplier)
        five_minutes_from_now_milli = current_epoch_milli + 300000
        while current_epoch_milli < five_minutes_from_now_milli:
            ticker = await self._get_ticker(ws, instruments[0]["instrument_name"])
            for instrument in instruments:
                instrument_name = instrument["instrument_name"]
                subscription_message = await listener.get_message(instrument_name)
                bids = subscription_message["params"]["data"]["bids"]
                asks = subscription_message["params"]["data"]["asks"]
                asks_price, asks_volume = depth_calculator.calculate_depth_price(self._depth, asks)
                bids_price, bids_volume = depth_calculator.calculate_depth_price(self._depth, bids)
                iv_b76_bid = self._get_iv(instrument, ticker, current_epoch_milli, bids_price)
                iv_b76_ask = self._get_iv(instrument, ticker, current_epoch_milli, asks_price)
                difference = iv_b76_ask - iv_b76_bid
                logger.debug(f"Spread for {instrument_name} is {difference * 100}% and iv_b76_bid is {iv_b76_bid} and iv_b76_ask is {iv_b76_ask}")
                if min(asks_volume, bids_volume) < self._depth:
                    if subscription_message["params"]["data"]["timestamp"] - last_valid_liquidity_spreads[instrument_name] >= sixty_seconds_in_millis:
                        logger.info(f"Instrument {instrument_name} has not had valid volume or spread for over 60 seconds")
                        lower_volume_str = "ask" if asks_volume < bids_volume else "bid"
                        low_liquidity_alerts[instrument_name] = f"had low {lower_volume_str} liquidity of {min(asks_volume, bids_volume)}"
                else:
                    last_valid_liquidity_spreads[instrument_name] = subscription_message["params"]["data"]["timestamp"]

                if difference >= self._spread_limit:
                    if subscription_message["params"]["data"]["timestamp"] - last_valid_spreads[instrument_name] >= sixty_seconds_in_millis:
                        logger.info(f"Spread has been too high for {instrument_name} for over 60 seconds")
                        low_spread_alerts[instrument_name] = f"had a spread of {difference * 100}%"
                else:
                    last_valid_spreads[instrument_name] = subscription_message["params"]["data"]["timestamp"]
                current_epoch_milli = int(time.time() * self._seconds_to_millis_multiplier)
        # I'm letting low liquidity alerts take precedence over low spread alerts, but this isn't a hard rule.
        return {**low_spread_alerts, **low_liquidity_alerts}

    async def _get_instrument_names_within_delta(self, ws) -> List[Dict]:
        instruments_within_delta = []
        for instrument in self._instruments:
            instrument_name = instrument["instrument_name"]
            ticker = await self._get_ticker(ws, instrument_name)
            instrument_delta = float(ticker["result"]["option_pricing"]["delta"])
            if self._delta <= abs(instrument_delta) <= 1 - self._delta:
                logger.debug(f"instrument is within delta 0 or 1: {instrument_delta} for instrument {instrument_name}")
                instruments_within_delta.append(instrument)
        return instruments_within_delta

    async def _send_messages_to_telegram(self, instruments_to_alert: Dict[str, str]) -> telegram.Message:
        message = f"""
        Alert! Within the last 5 minutes the following instruments were flagged for high spread width or low liquidity for an ETH depth of {self._depth * 2}.
        Spread threshold: {round(self._spread_limit * 100, 2)}%
        Liquidity threshold: {round(self._depth * 2, 2)} ETH

        Here are alerting instruments and their alert message:
        """ + "\n".join(
           sorted([f"{instrument}: {message}" for instrument, message in instruments_to_alert.items()])
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

    def _get_iv(self, instrument: Dict, ticker: Dict, current_epoch_milli: int, price: float) -> float:
        frwrd_price = float(ticker["result"]["option_pricing"]["forward_price"])
        strike_price = float(instrument["option_details"]["strike"])
        expiry = instrument["option_details"]["expiry"]
        datetime1 = datetime.fromtimestamp(current_epoch_milli / 1000)
        datetime2 = datetime.fromtimestamp(expiry)
        difference_in_years = (datetime2 - datetime1).total_seconds() / (365 * 24 * 60 * 60)
        is_call = instrument["option_details"]["option_type"] == "C"
        return utils.black76.iv_from_b76_price(price, strike_price, difference_in_years, frwrd_price, is_call)
