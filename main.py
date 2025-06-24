import json
import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
import aiohttp

# 로그 설정
logging.basicConfig(level=logging.INFO)

# 상태 정의
(COIN_NAME, COIN_PRICE, TARGET_PROFIT, ALERT_INTERVAL) = range(4)

# 사용자 데이터 저장 파일
USER_DATA_FILE = "user_data.json"

# 가격 조회 (Coingecko)
async def get_price(symbol: str) -> float:
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return data.get(symbol, {}).get("usd", 0.0)

def load_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# 입력 흐름
async def start_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🪙 코인 이름을 입력해주세요 (예: bitcoin):")
    return COIN_NAME

async def input_coin_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["coin"] = {"name": update.message.text}
    await update.message.reply_text("💰 매수 가격을 입력해주세요 (숫자만):")
    return COIN_PRICE

async def input_coin_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text)
        context.user_data["coin"]["price"] = price
        await update.message.reply_text("🎯 목표 수익률을 입력해주세요 (예: 10):")
        return TARGET_PROFIT
    except ValueError:
        await update.message.reply_text("❌ 숫자로 입력해주세요:")
        return COIN_PRICE

async def input_target_profit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        profit = float(update.message.text)
        context.user_data["coin"]["target"] = profit
        await update.message.reply_text("⏰ 알림 간격을 몇 분마다 할까요?")
        return ALERT_INTERVAL
    except ValueError:
        await update.message.reply_text("❌ 숫자로 입력해주세요:")
        return TARGET_PROFIT

async def input_alert_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        interval = int(update.message.text)
        context.user_data["coin"]["interval"] = interval

        user_id = str(update.message.chat_id)
        all_data = load_data()
        if user_id not in all_data:
            all_data[user_id] = []
        all_data[user_id].append(context.user_data["coin"])
        save_data(all_data)

        await update.message.reply_text("✅ 코인 정보가 저장되었습니다!")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ 숫자로 입력해주세요:")
        return ALERT_INTERVAL

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ 입력이 취소되었습니다.")
    return ConversationHandler.END

# 앱 실행
def main():
    TOKEN = "7634502846:AAEum3VRV2ZjhspSlJHXgsGsJh-m-KPnodc"
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("코인입력", start_input)],
        states={
            COIN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_coin_name)],
            COIN_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_coin_price)],
            TARGET_PROFIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_target_profit)],
            ALERT_INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_alert_interval)],
        },
        fallbacks=[CommandHandler("취소", cancel)],
    )

    app.add_handler(conv_handler)

    print("🤖 Bot Started...")
    app.run_polling()

if __name__ == "__main__":
    main()

