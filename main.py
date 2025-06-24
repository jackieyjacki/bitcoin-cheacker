import json
import os
import requests
import logging
from telegram import Bot
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
USER_ID = int(os.getenv("USER_ID"))

bot = Bot(token=BOT_TOKEN)
logging.basicConfig(level=logging.INFO)

with open("coins.json", "r") as f:
    coins = json.load(f)

def get_price(symbol):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol.lower()}&vs_currencies=krw"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get(symbol.lower(), {}).get("krw")
    return None

def check_profit():
    for coin, data in coins.items():
        current_price = get_price(coin)
        if current_price is None:
            continue
        buy_price = data["buy_price"]
        target_return = data["target_return"]
        profit_ratio = (current_price - buy_price) / buy_price
        message = f"[{coin}] 현재가: {current_price:,}원 | 수익률: {profit_ratio:.2%}"

        if profit_ratio >= target_return:
            message += " 🎯 목표 수익률 도달!"
        bot.send_message(chat_id=USER_ID, text=message)

if __name__ == "__main__":
    check_profit()
    scheduler = BlockingScheduler()
    scheduler.add_job(check_profit, "interval", minutes=10)
    scheduler.start()
