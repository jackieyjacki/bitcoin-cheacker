import os
import json
import logging
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackContext,
    ConversationHandler,
    MessageHandler,
    Filters
)
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

TOKEN = os.environ.get("TELEGRAM_TOKEN")
USER_ID = int(os.environ.get("TELEGRAM_USER_ID", "0"))
DATA_FILE = "coin_data.txt"

# 상태 정의
ASK_COIN, ASK_PRICE, ASK_TARGET, ASK_INTERVAL = range(4)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 유틸 함수: 데이터 저장/불러오기
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

# 코인가격 불러오기
async def get_current_price(symbol):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol.upper()}USDT"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            return float(data['price']) if 'price' in data else None

# 코인 입력 대화 흐름
def start_coin_input(update: Update, context: CallbackContext):
    update.message.reply_text("추적할 코인 이름을 입력하세요. (예: BTC)")
    return ASK_COIN

def ask_price(update: Update, context: CallbackContext):
    context.user_data["coin"] = update.message.text.upper()
    update.message.reply_text("매수 가격을 입력하세요 (KRW 기준):")
    return ASK_PRICE

def ask_target(update: Update, context: CallbackContext):
    try:
        context.user_data["buy_price"] = float(update.message.text)
    except ValueError:
        update.message.reply_text("숫자로 다시 입력해주세요.")
        return ASK_PRICE
    update.message.reply_text("목표 수익률을 입력하세요 (%):")
    return ASK_TARGET

def ask_interval(update: Update, context: CallbackContext):
    try:
        context.user_data["target"] = float(update.message.text)
    except ValueError:
        update.message.reply_text("숫자로 다시 입력해주세요.")
        return ASK_TARGET
    update.message.reply_text("알림 주기를 몇 분으로 할까요?")
    return ASK_INTERVAL

def finish_input(update: Update, context: CallbackContext):
    try:
        interval = int(update.message.text)
        coin = context.user_data["coin"]
        data = load_data()
        data[coin] = {
            "buy_price": context.user_data["buy_price"],
            "target": context.user_data["target"],
            "interval": interval
        }
        save_data(data)
        update.message.reply_text(f"{coin} 정보가 저장되었습니다.")
    except ValueError:
        update.message.reply_text("숫자로 다시 입력해주세요.")
        return ASK_INTERVAL
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("취소되었습니다.")
    return ConversationHandler.END

# 코인 수정/삭제 명령
def modify_coin(update: Update, context: CallbackContext):
    data = load_data()
    if not data:
        update.message.reply_text("저장된 코인이 없습니다.")
        return
    msg = "수정할 코인 이름과 항목을 입력해주세요. 예: BTC 가격 30000"
    update.message.reply_text(msg)

def delete_coin(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("삭제할 코인 이름을 입력해주세요. 예: /코인삭제 BTC")
        return
    coin = context.args[0].upper()
    data = load_data()
    if coin in data:
        del data[coin]
        save_data(data)
        update.message.reply_text(f"{coin} 삭제 완료")
    else:
        update.message.reply_text(f"{coin} 정보가 없습니다.")

# 주기적 알림
async def check_prices(context: CallbackContext):
    data = load_data()
    for coin, info in data.items():
        price = await get_current_price(coin)
        if not price:
            continue
        buy = info["buy_price"]
        rate = ((price - buy) / buy) * 100
        msg = f"{coin} 현재가: {price:.2f} USDT\n매수가: {buy} KRW\n수익률: {rate:.2f}%"

        # 조건별 멘트 변경
        if rate >= info["target"]:
            msg = f"🎯목표 수익률 도달!\n{msg}"
        elif rate >= 0.8 * info["target"]:
            msg = f"📈목표에 근접!\n{msg}"
        elif rate < 0:
            msg = f"📉 손실 상태입니다.\n{msg}"
        else:
            msg = f"📊현황 보고\n{msg}"

        await context.bot.send_message(chat_id=USER_ID, text=msg)

# 메인 실행
def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("코인입력", start_coin_input)],
        states={
            ASK_COIN: [MessageHandler(Filters.text & ~Filters.command, ask_price)],
            ASK_PRICE: [MessageHandler(Filters.text & ~Filters.command, ask_target)],
            ASK_TARGET: [MessageHandler(Filters.text & ~Filters.command, ask_interval)],
            ASK_INTERVAL: [MessageHandler(Filters.text & ~Filters.command, finish_input)],
        },
        fallbacks=[CommandHandler("취소", cancel)],
    )

    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler("코인수정", modify_coin))
    dp.add_handler(CommandHandler("코인삭제", delete_coin))

    # 스케줄러로 알림 시작
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: asyncio.run(check_prices(dp)),
        IntervalTrigger(minutes=5)
    )
    scheduler.start()

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
