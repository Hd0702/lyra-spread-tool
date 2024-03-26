import asyncio
import json
import logging
from typing import Dict, List

import websockets
from lyra.constants import LYRA_WEBSOCKET_URI

logger = logging.getLogger(__name__)


class SubscriptionListener:
    def __init__(self, instruments: List[str]):
        self._instrument_results: Dict[str, Dict | None] = {instrument: None for instrument in instruments}
        self._subscription_task: asyncio.Task | None = None
        self._ws: websockets.WebSocketClientProtocol | None = None

    async def create_subscription_task(self):
        subscription_message = {"id": "1", "method": "subscribe", "params": {
            "channels": [f"orderbook.{instrument}.1.100" for instrument in self._instrument_results.keys()]}}
        self._ws = await websockets.connect(LYRA_WEBSOCKET_URI)
        await self._ws.send(json.dumps(subscription_message))
        sub_response = json.loads(await self._ws.recv())
        if "result" not in sub_response or "status" not in sub_response["result"]:
            raise ValueError(f"Subscription failed with output {sub_response}")
        failed_subscriptions = []
        for instrument_name, status in sub_response["result"]["status"].items():
            if status != "ok":
                failed_subscriptions.append(instrument_name)
        if failed_subscriptions:
            raise ValueError(f"Failed to subscribe to instruments {failed_subscriptions}")
        self._subscription_task = asyncio.create_task(self._listen_to_messages())

    async def close(self):
        if self._subscription_task:
            self._subscription_task.cancel()
        if self._ws:
            await self._ws.close()

    async def get_message(self, instrument: str) -> Dict:
        retry_count = 0
        while not self._instrument_results[instrument]:
            if retry_count == 5:
                raise ValueError(
                    f"Failed to get message for {instrument} after {retry_count} retries. Please investigate.")
            logger.debug(f"Retrying to get message for {instrument}")
            await asyncio.sleep(1)
            retry_count += 1
        return self._instrument_results[instrument]

    async def _listen_to_messages(self):
        try:
            while True:
                response = json.loads(await self._ws.recv())
                logger.debug(f"Received response {response}")
                self._instrument_results[response["params"]["data"]["instrument_name"]] = response
        except Exception as e:
            self._subscription_task.cancel()
            await self._ws.close()
            raise e
