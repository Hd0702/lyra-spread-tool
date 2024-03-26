This is my solution to the Lyra order spread tool. it calculates low liquidity and spread discrepancies for options on the Lyra platform and sends them to Telegram to alert MMs.

## Arguments
It takes 6 arguments right now.

1. *expiry_date*: the expiry date for the option we want. This is in a format like yyyyMMdd or 20240329 as an example.
2. *delta*: this is the black scholes delta that comes from the [Lyra ticker](https://docs.lyra.finance/reference/public-get_ticker). This is used as a filter to remove options that have a delta that is too extreme. For example: if we input .03 then we keep options that have are .03 <= abs(delta) <= 1 - .03
3. *spread_limit*: This is the maximum spread tolerated between bids and asks for an option. This is essentially compared against asks iv - bids iv. If the spread calculated is greater than the spread limit for 60 seconds or more we will send an alert for that option.
4. *depth*: This is the maximum depth we are using to calculate bid and ask price. When calculating bid or ask prices we will get the best order up to the `depth / 2` inputted. For example if we input 10 then we will get the best bids for 5 ETH and asks for 5 ETH, and we will calculate the iv delta using those prices. **NOTE:** we also alert on this metric if we find that either bids or asks does not have enough liquidty to cover the price calculation. We currently emit these as a higher priority over spread alerts.
5. *telegram_key*: this is the private key for the telegram bot that will send the alerts. Message me if you want this.
6. *telegram_chat_id*: this is the chatroom id that the bot will send the alerts to.

The script will run until the expiry date is reached or by manual input. 

## How to run

I included a script file `start.sh` that will build the docker image and run the container. It currently runs on python 3.11 since that is the latest compatible version with our libraries.