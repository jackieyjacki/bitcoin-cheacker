import os
import json
import logging
import requests
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    ConversationHandler,
)
from apscheduler.schedulers.background import BackgroundScheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_FILE = "coin_data.txt"

ASK_NAME, ASK_BUY_PRICE, ASK_TARGET_PROFIT, ASK_INTERVAL = range(4)
user_states = {}
user_id = None

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_price(symbol):
    try:
        res = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT")
        return float(res.json()["price"])
    except:
        return None

def start_coin_input(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("등록할 코인 이름을 입력해주세요. (예: BTC)")
    return ASK_NAME

def ask_buy_price(update: Update, context: CallbackContext) -> int:
    context.user_data["symbol"] = update.message.text.upper()
    update.message.reply_text("매수 가격을 입력해주세요. (단위: USDT)")
    return ASK_BUY_PRICE

def ask_target_profit(update: Update, context: CallbackContext) -> int:
    context.user_data["buy_price"] = float(update.message.text)
    update.message.reply_text("목표 수익률을 입력해주세요. (예: 10%)")
    return ASK_TARGET_PROFIT

def ask_interval(update: Update, context: CallbackContext) -> int:
    context.user_data["target_profit"] = float(update.message.text.strip('%'))
    update.message.reply_text("알림 간격(초)을 입력해주세요.")
    return ASK_INTERVAL

def save_coin(update: Update, context: CallbackContext) -> int:
    interval = int(update.message.text)
    user_id = str(update.message.from_user.id)

    coin_data = load_data()
    if user_id not in coin_data:
        coin_data[user_id] = []

    coin_data[user_id].append({
        "symbol": context.user_data["symbol"],
        "buy_price": context.user_data["buy_price"],
        "target_profit": context.user_data["target_profit"],
        "interval": interval
    })

    save_data(coin_data)
    update.message.reply_text("코인 정보가 저장되었습니다.")
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("입력이 취소되었습니다.")
    return ConversationHandler.END

def modify_coin(update: Update, context: CallbackContext):
    update.message.reply_text("아직 미구현입니다. 다음 버전에서 제공됩니다.")

def delete_coin(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    coin_data = load_data()

    if user_id in coin_data and coin_data[user_id]:
        msg = "삭제할 코인 이름을 입력해주세요:\n"
        msg += "\n".join([c["symbol"] for c in coin_data[user_id]])
        update.message.reply_text(msg)
    else:
        update.message.reply_text("저장된 코인이 없습니다.")

    user_states[user_id] = "deleting"

def handle_text(update: Update, context: CallbackContext):
    user_id_str = str(update.message.from_user.id)
    if user_states.get(user_id_str) == "deleting":
        coin_data = load_data()
        symbol = update.message.text.upper()
        before = len(coin_data.get(user_id_str, []))
        coin_data[user_id_str] = [c for c in coin_data.get(user_id_str, []) if c["symbol"] != symbol]
        after = len(coin_data[user_id_str])
        save_data(coin_data)
        user_states[user_id_str] = None
        if before == after:
            update.message.reply_text("해당 코인을 찾을 수 없습니다.")
        else:
            update.message.reply_text("삭제되었습니다.")

def check_prices():
    coin_data = load_data()
    for uid, coins in coin_data.items():
        for coin in coins:
            current_price = fetch_price(coin["symbol"])
            if current_price:
                profit_rate = (current_price - coin["buy_price"]) / coin["buy_price"] * 100
                message = f"[{coin['symbol']}] 현재가: ${current_price:.2f}, 수익률: {profit_rate:.2f}%"
                if profit_rate >= coin["target_profit"]:
                    message += "\n🎯 목표 수익률 도달!"
                elif profit_rate >= 0:
                    message += "\n📈 상승 중입니다!"
                else:
                    message += "\n📉 하락 중입니다!"
                context = ContextCache.get(uid)
                if context:
                    context.bot.send_message(chat_id=int(uid), text=message)

class ContextCache:
    contexts = {}

    @classmethod
    def store(cls, user_id, context):
        cls.contexts[str(user_id)] = context

    @classmethod
    def get(cls, user_id):
        return cls.contexts.get(str(user_id), None)

def main():
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    if not TOKEN:
        print("TELEGRAM_TOKEN 환경변수를 설정하세요.")
        return

    updater = Updater(TOKEN)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("coin_input", start_coin_input)],
        states={
            ASK_NAME: [MessageHandler(Filters.text & ~Filters.command, ask_buy_price)],
            ASK_BUY_PRICE: [MessageHandler(Filters.text & ~Filters.command, ask_target_profit)],
            ASK_TARGET_PROFIT: [MessageHandler(Filters.text & ~Filters.command, ask_interval)],
            ASK_INTERVAL: [MessageHandler(Filters.text & ~Filters.command, save_coin)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler("coin_modify", modify_coin))
    dp.add_handler(CommandHandler("coin_delete", delete_coin))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    scheduler = BackgroundScheduler()
    scheduler.add_job(check_prices, "interval", seconds=60)
    scheduler.start()

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
