import argparse
import asyncio
import json
import logging
import sys

import websockets

import instrument_monitor
from lyra.constants import LYRA_WEBSOCKET_URI
from telegram_client.telegram_client import TelegramClient

logging.basicConfig(format="%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
                    datefmt="%Y-%m-%d:%H:%M:%S", level=logging.INFO)


async def run_monitor(arguments):
    async with websockets.connect(LYRA_WEBSOCKET_URI) as ws:
        print(arguments)
        get_instruments_message = {"id": "1", "method": "public/get_instruments",
                                   "params": {"currency": "ETH", "expired": False, "instrument_type": "option"}}
        await ws.send(json.dumps(get_instruments_message))
        response = json.loads(await ws.recv())
        instruments = list(filter(lambda instrument: arguments.expiry_date in instrument["instrument_name"], response["result"]))
        telegram_client = TelegramClient(arguments.telegram_key, arguments.telegram_chat_id)
        monitor = instrument_monitor.InstrumentMonitor(instruments, arguments.spread_limit, arguments.depth, arguments.delta, telegram_client)
        await monitor.start_monitor()


def main():
    print(f"{sys.argv}")
    parser = argparse.ArgumentParser(description="Monitor instruments for a given expiry date")
    parser.add_argument("--expiry_date", type=str, default="20240329", help="The expiry date for options to monitor")
    parser.add_argument("--delta", type=float, default=.03, help="The black-scholes delta threshold")
    parser.add_argument("--spread_limit", type=float, default=.03, help="The spread limit for alerts")
    parser.add_argument("--depth", type=float, default=100, help="The depth for calculating the price")
    parser.add_argument("--telegram_key", type=str, help="The telegram key for sending alerts")
    parser.add_argument("--telegram_chat_id", type=int, default=-1002075187090, help="The telegram chat id for sending alerts")
    args = parser.parse_args()
    asyncio.run(run_monitor(args))

# uncomment to run locally
# if __name__ == "__main__":
#     main()
