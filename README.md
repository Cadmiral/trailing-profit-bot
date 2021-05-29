# trailing-profit-bot
## What is it?

An automated trading bot for use with TradingView Strategies to execute cryptocurrency trades on Binance.com, written in Python. The python script runs its own trailing loss/profit vs using built-in trailers from the exchanges.  This gives users more flexibility in terms of how and when to trail stops. 

## Requirements:

For an out of the box solution, you'll need:

Tradingview - for creating trading strategies and algorithms (https://www.tradingview.com/) \
Binance - Broker/Exchange (https://www.binance.com) \
Telegram Messaging - for message notifications (https://telegram.org/) \
ngrok - webserver for receiving webhook calls from TradingView (https://ngrok.com/)

These can be substituted for your preferred services, with some modifications to the api calls.  

## How it all works:

This bot is intended for those who have preconfigured trading strategies/algorithms created on software platforms that supports webhook calls, i.e TradingView.  Here is the order flow:

1. Create trade alerts for your strategy/algorithm on TradingView
2. Alert message should be formated as json (for example, run generate_alert_message.py) 
3. Include the listening webhook url to forward the message to your webserver
4. Webserver receives the message and checks states and config
5. Orders are sent to Binance (order logic is in order.py) 


## Configuration files:

config.txt - telegram and webserver port config \
state.cfg - can be used to hold state information, such as the multi-timeframe trends (not currently implemented in this version).  It also checks wheher there is already a trade running of the same security (see example file).

## Troubleshooting:

- ngrok Webserver authentication is configured in auth.py.  Running generate_alert_message.py will give you the auth key in the message.
- A logs/ subfolder will need to be created for logs
- Binance api key/secret reads from your system profile (~/.profile for most *nix distro)
- Use this link for a guide on how to set up your Telegram notification bot: https://core.telegram.org/bots
- Modify util.py to use with your telegram bot
