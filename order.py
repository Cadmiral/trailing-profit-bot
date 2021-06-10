import configparser
import os
import pprint
import time

import util

from binance.client import Client
from binance.exceptions import BinanceAPIException

class OrderMgr:

    STATE_CONFIG = "state.cfg"

    def __init__(self, api_key, api_secret):
        self.client = Client(api_key, api_secret)
        self.log = util.getLogger("order_mgr")
        self.config = configparser.ConfigParser()
        try:
            self.config.read(OrderMgr.STATE_CONFIG)
        except Exception as e:
            self.log.exception("Could not read config file %s: %s", path, e)
            self.config = None

    def write_config(self, path=None):
        if not path:
            path = OrderMgr.STATE_CONFIG

        success = False
        try:
            self.log.debug("Write config file: %s", path)
            with open(path, "w") as configFile:
                self.config.write(configFile)

            success = True
        except Exception as e:
            self.log.exception("Could not write config to file %s: %s", path, e)

        return success

    def get_quantity_precision(self, symbol):    
        info = self.client.futures_exchange_info() 
        info = info['symbols']
        for x in range(len(info)):
            if info[x]['symbol'] == symbol:
                return info[x]['quantityPrecision']
        return None

    def get_price_precision(self, symbol):    
        info = self.client.futures_exchange_info() 
        info = info['symbols']
        for x in range(len(info)):
            if info[x]['symbol'] == symbol:
                return info[x]['pricePrecision']
        return None

    def get_balance(self, symbol="USDT", timeout=0, sleep=1):
        self.log.info("Get balance for %s", symbol)
        balance = 0.0
        balances = None
        t0 = time.time()
        while balances is None:
            if timeout > 0:
                t1 = time.time()
                if (t1 - t0) > timeout:
                    self.log.warning("Timeout: Exceeded %s seconds", timeout)
                    return balance

            try:
                balances = self.client.futures_account_balance()
                self.log.debug("futures_account_balance: %s",
                               pprint.pformat(balances))
            except BinanceAPIException as e:
                self.log.exception("BinanceAPIException: %s", e)
            except Exception as e:
                self.log.exception("Unexpected Error: %s", e)
            finally:
                time.sleep(sleep)

        for b in balances:
            if b["asset"] == symbol:
                balance = float(b["balance"])
                break

        return balance

    def create_order(self, orderType=None, symbol=None, side=None,
                     quantity=None, price=0.0, timeout=0, sleep=1, stopPrice=0.0, 
                     positionAmt=None):

        precision_price = self.get_price_precision(symbol)
        precision_quantity = self.get_quantity_precision(symbol)
        
        if not quantity:
            quantity = float("{0:.{1}f}".format(quantity, precision_quantity))
        price = "{0:.{1}f}".format(price, precision_price)
        stopPrice = "{0:.{1}f}".format(stopPrice, precision_price)

        self.log.info("Create %s %s order for %s: quantity=%s, price=%s, positionAmt=%s, stopPrice=%s",
                      orderType, side, symbol, quantity, price, positionAmt, stopPrice)

        order = None
        t0 = time.time()
        while order is None:
            if timeout > 0:
                t1 = time.time()
                if (t1 - t0) > timeout:
                    self.log.warning("Timeout: Exceeded %s seconds", timeout)
                    return
            try:
                if quantity == 0.0:
                    self.log.info("Order Quantity is 0, time to exit", timeout)
                    order = self.client.futures_create_order(symbol=symbol, side=side, 
                    type='MARKET', quantity=positionAmt, reduceOnly='true')
                    return
                elif orderType == "LIMIT":
                    order = self.client.futures_create_order(
                        symbol=symbol, side=side, type=orderType,
                        timeInForce="GTC", quantity=quantity, price=price)
                elif orderType == "TAKE_PROFIT_MARKET":
                    order = self.client.futures_create_order(
                        symbol=symbol, side=side, type=orderType,
                        quantity=quantity, stopPrice=stopPrice, reduceOnly=True)
                elif orderType == "STOP_MARKET":
                    order = self.client.futures_create_order(
                        symbol=symbol, side=side, type=orderType,
                        stopPrice=stopPrice, closePosition=True)
                else:
                    order = self.client.futures_cancel_all_open_orders(symbol=symbol)
                self.log.debug("futures_create_order: %s", pprint.pformat(order))
            except BinanceAPIException as e:
                self.log.exception("BinanceAPIException: %s", e)
                message = "Exception occurred: Closing out all Positions", symbol
                order = self.client.futures_create_order(symbol=symbol, side=side, 
                    type='MARKET', quantity=positionAmt, reduceOnly='true')
                self.log.info(message)
                util.sendTelegram(message)
            except Exception as e:
                self.log.exception("Unexpected Error: %s", e)
                message = "Exception occurred: Closing out all Positions", symbol
                order = self.client.futures_create_order(symbol=symbol, side=side, 
                    type='MARKET', quantity=positionAmt, reduceOnly='true')

                self.log.info(message)
                util.sendTelegram(message)
            finally:
                time.sleep(sleep)

        return order

    def get_order(self, symbol, orderId, status=[], timeout=0, sleep=1):
        self.log.info("Get %s order with ID: %s", symbol, orderId)
        order = None
        t0 = time.time()
        while order is None:
            if timeout > 0:
                t1 = time.time()
                if (t1 - t0) > timeout:
                    self.log.warning("Timeout: Exceeded %s seconds", timeout)
                    return

            try:
                order = self.client.futures_get_order(symbol=symbol,
                                                      orderId=orderId)
                self.log.debug("futures_get_order: %s", pprint.pformat(order))
                if order:
                    # Check that order has given status
                    if status and order["status"] not in status:
                        self.log.warning("Order status: %s, waiting to be %s",
                                         order["status"], " or ".join(status))
                        order = None
            except BinanceAPIException as e:
                self.log.exception("BinanceAPIException: %s", e)
            except Exception as e:
                self.log.exception("Unexpected Error: %s", e)
            finally:
                time.sleep(sleep)

        return order

    def get_open_orders(self, symbol, timeout=0, sleep=1):
        self.log.info("Get open orders for %s", symbol)
        orders = None
        t0 = time.time()
        while orders is None:
            if timeout > 0:
                t1 = time.time()
                if (t1 - t0) > timeout:
                    self.log.warning("Timeout: Exceeded %s seconds", timeout)
                    return []

            try:
                orders = self.client.futures_get_open_orders(symbol=symbol)
                self.log.debug("futures_get_open_orders: %s",
                               pprint.pformat(orders))
            except BinanceAPIException as e:
                self.log.exception("BinanceAPIException: %s", e)
            except Exception as e:
                self.log.exception("Unexpected Error: %s", e)

        return orders

    def send_order(self, data, timeout=250.0):
        self.log.info("Send order: %s", pprint.pformat(data))

        orderType = data["type"]
        symbol = data["symbol"]
        side = data["side"]
        price = float(data["price"])
        takeProfit = float(data["take_profit"])
        stopLoss = float(data["stop_loss"])
        percentageVal = float(data["percentage"])
        strategy = data["strategy"]
        precision_price = self.get_price_precision(symbol)
        precision_quantity = self.get_quantity_precision(symbol)
        # Adjust order quantity
        balance = self.get_balance()
        percentage = percentageVal / 100.0

        stopLossAmt = abs(price - stopLoss)
        maxStopLossAmt = float(balance * percentage)
        quantity = maxStopLossAmt / stopLossAmt

        self.log.debug("stopLossAmt=%.2f, maxStopLossAmt=%.2f, quantity=%s",
                       stopLossAmt, maxStopLossAmt, quantity)

        # Create new order
        t0 = time.time()
        order = self.create_order(orderType=orderType, symbol=symbol,
                                  side=side, quantity=quantity, price=price,
                                  timeout=timeout)
        t1 = time.time()
        timeout -= (t1 - t0)
        if timeout <= 0.0:
            self.client.futures_cancel_all_open_orders(symbol=symbol)
            util.sendTelegram("Order Limit Timeout: Exceeded 5 minutes")
            return False

        if order is None:
            self.log.error("Could not create order")
            return False

        # Send telegram
        message = ("Create New Order for: {4}\nSide: {5}\nPercentage: {6}\nPrice: ${0:,.2f}\nQuantity: {3:.2f}\nTake Profit: ${1:,.2f}\nStop Loss: ${2:,.2f}\nOpening Balance: ${8:,.2f}\nMax Loss: ${7:,.2f}".format(
                    price, takeProfit, stopLoss, quantity, symbol, side, percentage, maxStopLossAmt, balance))

        util.sendTelegram(message)

        # Get order by ID
        orderId = order["orderId"]
        t0 = time.time()
        order = self.get_order(symbol, orderId,
                               status=["FILLED", "PARTIALLY_FILLED"],
                               timeout=timeout)
        t1 = time.time()
        timeout -= (t1 - t0)
        if timeout <= 0.0:
            self.client.futures_cancel_all_open_orders(symbol=symbol)
            util.sendTelegram("Order Limit Timeout: Exceeded 5 minutes")
            return False

        if order is None:
            self.log.error("Could not get order with ID: %s", orderId)
            self.log.info("Cancel all open orders for %s", symbol)
            self.client.futures_cancel_all_open_orders(symbol=symbol)
            util.sendTelegram("Order Limit Timeout: Exceeded 5 minutes")
            return False

        if order["status"] == "PARTIALLY_FILLED":
            # Wait a little more time to see if order fills
            time.sleep(5)
            order = self.client.futures_get_order(symbol=symbol,
                                                  orderId=orderId)
            self.log.info("Cancel all open orders for %s", symbol)
            self.client.futures_cancel_all_open_orders(symbol=symbol)

        if side == "BUY":
            self.send_long_orders(order, takeProfit, stopLoss, balance, strategy)
        else:
            self.send_short_orders(order, takeProfit, stopLoss, balance, strategy)

        return True

    def create_stop_loss_trailing_order(self, symbol, side, stop_loss_orderType, 
        stop_loss, iteration, positionAmt):

        message = ("Moving Stop Loss ({0}), symbol={1}new stop_price={2:,.2f}, positionAmt={3}".format(iteration, symbol, stop_loss, positionAmt))
        self.log.info(message)
        util.sendTelegram(message)

        stop_loss_order = self.create_order(orderType=stop_loss_orderType, symbol=symbol,
            side=side, stopPrice=stop_loss, positionAmt=positionAmt)

        return stop_loss_order

    def send_short_orders(self, order, take_profit, stop_loss, open_balance, strategy):
        self.log.info("Set TP and SL short order: take_profit=%s, stop_loss=%s",
                       take_profit, stop_loss)
        self.log.debug(pprint.pformat(order))

        open_balance=float(open_balance)
        take_profit_orderType = "TAKE_PROFIT_MARKET"
        stop_loss_orderType = "STOP_MARKET"
        side = "BUY"
        symbol = order["symbol"]
        if strategy == "highVol":
            quantity_multiplier = 1
        else:
            quantity_multiplier = 0.5
        stop_loss_muliplier = 0.5
        order_quantity = float(order["executedQty"])
        price = float(order["avgPrice"])
        atr = abs(price - take_profit)
        order_quantity = abs(order_quantity * quantity_multiplier)

        openPosition = self.client.futures_position_information(symbol=symbol)
        for p in openPosition:
            if p["symbol"] == symbol:
                positionAmt = abs(float(p["positionAmt"]))

        stop_loss_order = self.create_order(
            symbol=symbol, side=side, orderType=stop_loss_orderType,
            stopPrice=stop_loss, positionAmt=positionAmt)

        self.log.debug("Stop loss order: %s", pprint.pformat(stop_loss_order))

        take_profit_dict = {}
        for number in range(1, 6):
            take_profit_dict["take_profit_order%s" %number] = self.create_order(orderType=take_profit_orderType, symbol=symbol,
                side=side, quantity=order_quantity, stopPrice=take_profit, 
                positionAmt=positionAmt)
            order_quantity = float(order_quantity) * 0.5
            # if symbol not in set(["BTCUSDT", "ETHUSDT"]):
            #     order_quantity = int(order_quantity)
            # else:
            #     order_quantity = "{:.3f}".format(order_quantity)
            take_profit = take_profit - atr * 0.5
            time.sleep(1)
            self.log.debug("Take profit%s order: %s", number, take_profit_dict["take_profit_order%s" %number])
        
        iteration = 1
        stop_loss_order_status = "NEW"
        while stop_loss_order_status != "FILLED" and iteration < 6:

            self.log.debug("TP{0} and SL{0} positions are still open".format(iteration))
            
            stop_loss_order = self.client.futures_get_order(symbol=symbol, orderId=stop_loss_order['orderId'])            
            stop_loss_order_status = stop_loss_order["status"] 
            
            take_profit_order = take_profit_dict["take_profit_order%s" %iteration]
            take_profit_oder_id = take_profit_order['orderId']
            take_profit_get_order = self.client.futures_get_order(symbol=symbol, orderId=take_profit_oder_id)
            take_profit_order_status = take_profit_get_order["status"]
            take_profit_quantity = take_profit_get_order["executedQty"]

            openPosition = self.client.futures_position_information(symbol=symbol)
            for p in openPosition:
                if p["symbol"] == symbol:
                    positionAmt = abs(float(p["positionAmt"]))

            if positionAmt == 0.0: 
                break

            if take_profit_order_status == "FILLED":
                profitPrice = float(take_profit_get_order["avgPrice"])
                profit = (price - profitPrice) * float(take_profit_quantity)
                self.log.info("price= {0}, profitPrice= {1}, quantity= {2}".format(price, profitPrice, take_profit_quantity))
                message = "TP{0} Profit: ${1:.2f}, symbol: {2}".format(iteration, profit, symbol)
                self.log.info(message)
                util.sendTelegram(message)
                atr_multiplier = 0.5

        #         #Create Stop Loss Order
                if iteration == 2:
                    stop_loss = stop_loss + atr
                    stop_loss_order = self.create_stop_loss_trailing_order(symbol, side, stop_loss_orderType, 
                                  stop_loss, iteration, positionAmt)
                elif iteration >= 3 :
                    stop_loss = price - (atr * atr_multiplier * (iteration-2)) # move stopLoss to 50% atr increments after TP3 reached
                    stop_loss_order = self.create_stop_loss_trailing_order(symbol, side, stop_loss_orderType, 
                                  stop_loss, iteration, positionAmt)
                iteration += 1
            time.sleep(1)

        self.log.info("StopLoss {0}: Cancelling all open orders for {1}".format(iteration, symbol))
        self.client.futures_cancel_all_open_orders(symbol=symbol)
        end_balance = self.get_balance()
        loss = end_balance - open_balance
        message = "Total Profit/Loss: ${0:.2f}, symbol: {1}\nEnding Balance: ${2:,.2f}".format(loss, symbol, end_balance)
        self.log.info(message)
        util.sendTelegram(message)
        #add one last failsafe
        openPosition = self.client.futures_position_information(symbol=symbol)
        for p in openPosition:
            if p["symbol"] == symbol:
                positionAmt = abs(float(p["positionAmt"]))
                if positionAmt != 0.0: 
                    self.client.futures_create_order(symbol=symbol, side=side, 
                    type='MARKET', quantity=positionAmt, reduceOnly='true')

    def send_long_orders(self, order, take_profit, stop_loss, open_balance, strategy):
        self.log.info("Set TP and SL short order: take_profit=%s, stop_loss=%s",
                       take_profit, stop_loss)
        self.log.debug(pprint.pformat(order))

        open_balance=float(open_balance)
        take_profit_orderType = "TAKE_PROFIT_MARKET"
        stop_loss_orderType = "STOP_MARKET"
        side = "SELL"
        symbol = order["symbol"]
        if strategy == "highVol":
            quantity_multiplier = 1
        else:
            quantity_multiplier = 0.5
        quantity_multiplier = 0.5
        stop_loss_muliplier = 0.5
        order_quantity = float(order["executedQty"])
        price = float(order["avgPrice"])
        atr = abs(price - take_profit)
        quantityVal = abs(order_quantity * quantity_multiplier)
        if symbol not in set(["BTCUSDT", "ETHUSDT"]):
            quantityVal = int(quantityVal)
        order_quantity = "{:.2f}".format(quantityVal)

        openPosition = self.client.futures_position_information(symbol=symbol)
        for p in openPosition:
            if p["symbol"] == symbol:
                positionAmt = abs(float(p["positionAmt"]))

        stop_loss_order = self.create_order(
            symbol=symbol, side=side, orderType=stop_loss_orderType,
            stopPrice="{:.2f}".format(stop_loss), positionAmt=positionAmt)

        self.log.debug("Stop loss order: %s", pprint.pformat(stop_loss_order))

        take_profit_dict = {}
        for number in range(1, 6):
            take_profit_dict["take_profit_order%s" %number] = self.create_order(orderType=take_profit_orderType, symbol=symbol,
                side=side, quantity=order_quantity, stopPrice="{:.2f}".format(take_profit), 
                positionAmt=positionAmt)
            order_quantity = float(order_quantity) * 0.5
            if symbol not in set(["BTCUSDT", "ETHUSDT"]):
                order_quantity = int(order_quantity)
            else:
                order_quantity = "{:.3f}".format(order_quantity)
            take_profit = take_profit + atr * 0.5
            time.sleep(1)
            self.log.debug("Take profit%s order: %s", number, take_profit_dict["take_profit_order%s" %number])
        
        iteration = 1
        stop_loss_order_status = "NEW"
        while stop_loss_order_status != "FILLED" and iteration < 6:

            self.log.debug("TP{0} and SL{0} positions are still open".format(iteration))
            
            stop_loss_order = self.client.futures_get_order(symbol=symbol, orderId=stop_loss_order['orderId'])            
            stop_loss_order_status = stop_loss_order["status"] 
            
            take_profit_order = take_profit_dict["take_profit_order%s" %iteration]
            take_profit_oder_id = take_profit_order['orderId']
            take_profit_get_order = self.client.futures_get_order(symbol=symbol, orderId=take_profit_oder_id)
            take_profit_order_status = take_profit_get_order["status"]
            take_profit_quantity = take_profit_get_order["executedQty"]

            openPosition = self.client.futures_position_information(symbol=symbol)
            for p in openPosition:
                if p["symbol"] == symbol:
                    positionAmt = abs(float(p["positionAmt"]))

            if positionAmt == 0.0: 
                break

            if take_profit_order_status == "FILLED":
                profitPrice = float(take_profit_get_order["avgPrice"])
                profit = (profitPrice - price) * float(take_profit_quantity)
                self.log.info("price= {0}, profitPrice= {1}, quantity= {2}".format(price, profitPrice, take_profit_quantity))
                message = "TP{0} Profit: ${1:.2f}, symbol: {2}".format(iteration, profit, symbol)
                self.log.info(message)
                util.sendTelegram(message)

                atr_multiplier = 0.5

        #         #Create Stop Loss Order
                if iteration == 2:
                    stop_loss = stop_loss + atr
                    stop_loss_order = self.create_stop_loss_trailing_order(symbol, side, stop_loss_orderType, 
                                  stop_loss, iteration, positionAmt)
                elif iteration >= 3 :
                    stop_loss = price + (atr * atr_multiplier * (iteration-2)) # move stopLoss to 50% atr increments after TP3 reached
                    stop_loss_order = self.create_stop_loss_trailing_order(symbol, side, stop_loss_orderType, 
                                  stop_loss, iteration, positionAmt)
                iteration += 1
            time.sleep(1)

        self.log.info("SL{0}: Cancelling all open orders for {1}".format(iteration, symbol))
        self.client.futures_cancel_all_open_orders(symbol=symbol)
        end_balance = self.get_balance()
        loss = end_balance - open_balance
        message = "Total Profit/Loss: ${0:.2f}, symbol: {1}\nEnding Balance: ${2:,.2f}".format(loss, symbol, end_balance)
        self.log.info(message)
        util.sendTelegram(message)
        #add one last failsafe
        openPosition = self.client.futures_position_information(symbol=symbol)
        for p in openPosition:
            if p["symbol"] == symbol:
                positionAmt = abs(float(p["positionAmt"]))
                if positionAmt != 0.0: 
                    self.client.futures_create_order(symbol=symbol, side=side, 
                    type='MARKET', quantity=positionAmt, reduceOnly='true')