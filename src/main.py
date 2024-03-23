import argparse
import asyncio
import json
import logging
import sys

import websockets

import instrument_monitor

logging.basicConfig(format="%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
                    datefmt="%Y-%m-%d:%H:%M:%S", level=logging.DEBUG)


async def main(expiry_date: str, delta: float, spread_limit: float, depth: float):
    print(f"Expiry date: {expiry_date}, Delta: {delta}, Spread limit: {spread_limit}, Depth: {depth}")
    async with websockets.connect("wss://api.lyra.finance/ws") as ws:
        get_instruments_message = {"id": "1", "method": "public/get_instruments",
                                   "params": {"currency": "ETH", "expired": False, "instrument_type": "option"}}
        await ws.send(json.dumps(get_instruments_message))
        response = json.loads(await ws.recv())
        instruments = list(filter(lambda instrument: expiry_date in instrument["instrument_name"], response["result"]))
        monitor = instrument_monitor.InstrumentMonitor(instruments, spread_limit, depth, delta)
        await monitor.start_monitor()


if __name__ == "__main__":
    print(f"{sys.argv}")
    parser = argparse.ArgumentParser(description="Monitor instruments for a given expiry date")
    parser.add_argument("--expiry_date", type=str, default="20240329", help="The expiry date for options to monitor")
    parser.add_argument("--delta", type=float, default=.03, help="The black-scholes delta threshold")
    parser.add_argument("--spread_limit", type=float, default=.03, help="The spread limit for alerts")
    parser.add_argument("--depth", type=float, default=20, help="The depth for calculating the price")
    args = parser.parse_args()
    asyncio.run(main(args.expiry_date, args.delta, args.spread_limit, args.depth))
