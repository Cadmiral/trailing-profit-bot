
import logging
import os

LOG_DIR = "logs"

TELEGRAM_BOT_TOKEN = "telgram:botTokenHere"
TELEGRAM_BOT_CHAT_ID = "telegramChatIDHere"
TELEGRAM_BOT_URL = "https://api.telegram.org/bot"


def parse_webhook(webhook_data):
    """
    This function takes the string from tradingview and turns it into a
    python dict.

        :param webhook_data: POST data from tradingview, as a string.
        :return: Dictionary version of string.
    """
    import ast
    data = ast.literal_eval(webhook_data)
    return data


def getLogger(name, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if len(logger.handlers) == 0:
        # Add file handler which logs debug messages
        import datetime
        dateStr = datetime.datetime.today().strftime("%Y-%m-%d")
        logName = "{0}_{1}.log".format(name, dateStr)
        logPath = os.path.join(LOG_DIR, logName)
        fh = logging.FileHandler(logPath)
        fh.setFormatter(logging.Formatter(
            fmt="[%(asctime)s] %(levelname)-8s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"))
        fh.setLevel(logging.DEBUG)
        logger.addHandler(fh)

        # Add console handler with higher log level
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter(
            "[%(name)s] %(levelname)-8s: %(message)s"))
        ch.setLevel(level)
        logger.addHandler(ch)

    return logger


def sendTelegram(message, token=TELEGRAM_BOT_TOKEN, chat_id=TELEGRAM_BOT_CHAT_ID):
    import requests
    params = {
        "chat_id": chat_id,
        "parse_mode": "Markdown",
        "text": message
    }
    sendURL = TELEGRAM_BOT_URL + token + "/sendMessage"
    response = requests.get(sendURL, params=params)
    return response.json()


def getConfig(path):
    if not os.path.isfile(path):
        return

    config = None
    try:
        import configparser
        config = configparser.ConfigParser()
        config.read(path)
    except Exception as e:
        config = None

    return config

