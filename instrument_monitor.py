from typing import Dict

import websockets


class InstrumentMonitor:
    def __init__(self, instrument: Dict):
        self.instrument = instrument

    # async def start_monitor(self):
    #     # for now each monitor will have its own WS connection
    #     # eventually we will have a single WS connection that will be shared by all monitors
    #     # but for now, this is an easy start
    #     uri = "wss://api.lyra.finance/ws"  # Use the actual WebSocket URI of Lyra Orderbook
    #     # monitor lyra orderbook channel https://docs.lyra.finance/reference/orderbook-instrument_name-group-depth
    #     async with websockets.connect(uri) as websocket:
    #         # Construct the subscription message according to Lyra's API documentation
    #         subscription_message = {
    #             "id": "1",
    #             "method": "public/get_instruments",
    #             "params": {
    #                 "currency": "ETH",
    #                 "expired": False,
    #                 "instrument_type": "option"
    #             }
    #         }
    #         while True:
    #             # Send the subscription message
    #             await websocket.send(json.dumps(subscription_message))
    #
    #             response = json.loads(await websocket.recv())
