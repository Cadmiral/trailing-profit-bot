import os
import pprint
import sys

from auth import get_token
from flask import Flask, request, abort

from order import OrderMgr
import util

# Create Flask object called app.
app = Flask(__name__)

# Create root to easily let us know its on/working.
@app.route("/")
def root():
    return "online"

@app.route("/webhook", methods=["POST"])
def webhook():
    if request.method == "POST":
        # Parse the string data from tradingview into a python dict
        data = util.parse_webhook(request.get_data(as_text=True))

        # Check that the key is correct
        if get_token() == data["key"]:
            log = util.getLogger("webhook")
            log.info(" [ALERT RECEIVED] ")
            log.debug(pprint.pformat(data))

            api_key = os.environ.get("binance_api")
            api_secret = os.environ.get("binance_secret")

            mgr = OrderMgr(api_key, api_secret)
            if not mgr.config:
                log.error("Could not read config")
                sys.exit(1)

            strategy = data["strategy"]
            symbol = data["symbol"]
            if not mgr.config.has_section(symbol):
                log.error("No config state for %s", symbol)
                sys.exit(1)

            symbolState = mgr.config.get(symbol, "state")
            #log.info("%s strategy: %s, state: %s", symbol, strategy, symbolState)
            if strategy == "state":
                if symbolState:
                    log.debug("state: %s", pprint.pformat(symbolState))
                    mgr.config.set(symbol, "state", data["trend"])
                    mgr.write_config()
                else:
                    log.warning("No state for symbol: %s", symbol)
                return "", 200
            elif strategy == "trend":
                isRunning = mgr.config.getboolean(symbol, "isrunning")
                if isRunning:
                    log.warning("%s trade is running, no trade", symbol)
                    return "", 200
                mgr.config.set(symbol, "isrunning", "yes")
                mgr.write_config()
                mgr.send_order(data)
                mgr.config.set(symbol, "isrunning", "no")
                mgr.write_config()
                return "", 200
            elif strategy == "scalp":
                isRunning = mgr.config.getboolean(symbol, "isrunning")
                if isRunning:
                    log.warning("%s trade is running, no trade", symbol)
                    return "", 200
                mgr.config.set(symbol, "isrunning", "yes")
                mgr.write_config()
                mgr.send_order(data)
                mgr.config.set(symbol, "isrunning", "no")
                mgr.write_config()
                return "", 200    
            elif strategy == "highVol":
                isRunning = mgr.config.getboolean(symbol, "isrunning")
                if isRunning:
                    log.warning("%s trade is running, no trade", symbol)
                    return "", 200
                mgr.config.set(symbol, "isrunning", "yes")
                mgr.write_config()
                mgr.send_order(data)
                mgr.config.set(symbol, "isrunning", "no")
                mgr.write_config()
                return "", 200    
            else:
                log.warning("Unhandled strategy: %s", strategy)
                return "", 200
        else:
            log.warning("Unknown key: %s", data["key"])
            abort(403)
    else:
        log.warning("Unhandled method: %s", request.method)
        abort(400)
if __name__ == "__main__":
    config = util.getConfig("config.txt")
    if config:
        port = config.get("webhook", "port")
        app.run(host="localhost", port=port)
    else:
        sys.exit("Invalid config file: config.txt")

