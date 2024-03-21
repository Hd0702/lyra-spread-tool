import asyncio
import json
import websockets
import utils.constants


# async def main():
#     async with websockets.connect(utils.constants.LYRA_INSTRUMENTS_URI) as ws:
#         await ws.send('{"type":"subscribe","channel":"instruments"}')
#         response = await ws.recv()
#         print(response)


async def main(expiry_date: str, num):
    uri = "wss://api.lyra.finance/ws"  # Use the actual WebSocket URI of Lyra Orderbook
    async with websockets.connect(uri) as websocket:
        # Construct the subscription message according to Lyra's API documentation
        subscription_message = {
            "id": "1",
            "method": "public/get_instruments",
            "params": {
                "currency": "ETH",
                "expired": False,
                "instrument_type": "option"
            }
        }
        while True:
            # Send the subscription message
            await websocket.send(json.dumps(subscription_message))

            response = json.loads(await websocket.recv())
            # TODO: Is it safe to use the expiry timestamp instead of parsing the instrument name? Feels unsafe in case instrument name changes format
            results = list(filter(lambda result: expiry_date in result["instrument_name"], response["result"]))
            print(f"Received message: {results}")
            print(f"For number {num}")
            # now we will
            # await asyncio.sleep(3)  # Sleep for 1 hour

# async def innterMain():
#     expiry_date = "20240329"
#     await asyncio.gather(
#         main(expiry_date, 0),
#         main(expiry_date, 1),
#         main(expiry_date, 2),
#         main(expiry_date, 3),
#         main(expiry_date, 4),
#         # add 5 more
#         main(expiry_date, 5),
#         main(expiry_date, 6),
#         main(expiry_date, 7),
#         main(expiry_date, 8),
#
#     )

async def test():
    uri = "wss://api.lyra.finance/ws"  # Use the actual WebSocket URI of Lyra Orderbook
    async with websockets.connect(uri) as websocket:
        # Construct the subscription message according to Lyra's API documentation
        subscription_message = {
            "id": "1",
            "method": "subscribe",
            "params": {
                "channels": ["orderbook.ETH-20240329-4200-C.1.100"]
            }
        }
        await websocket.send(json.dumps(subscription_message))
        response = json.loads(await websocket.recv())
        print(f"Found response {response}")
        while True:
            response = json.loads(await websocket.recv())
            print(f"Found response {response}")


async def unsubscribe():
    uri = "wss://api.lyra.finance/ws"  # Use the actual WebSocket URI of Lyra Orderbook
    async with websockets.connect(uri) as websocket:
        # Construct the subscription message according to Lyra's API documentation
        subscription_message = {
            "id": "1",
            "method": "unsubscribe",
            "params": {
            }
        }
        await websocket.send(json.dumps(subscription_message))
        response = json.loads(await websocket.recv())
        print(f"Found unsub response {response}")


if __name__ == "__main__":
    # looks like there is a get instruments websocket API that returns active instruments https://docs.lyra.finance/reference/public-get_instruments
    # we should double check if this is true. Their documentaion for their REST API actually returns some non-active instruments
    expiry_date = "20240329"
    # asyncio.run(innterMain())
    # asyncio.run(test())
    asyncio.run(unsubscribe())
    # asyncio.run(main(expiry_date, 0))
