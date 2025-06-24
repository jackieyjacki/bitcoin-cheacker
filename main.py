import logging
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)
import os

# 상태 정의
COIN_NAME, COIN_PRICE, TARGET_PROFIT, INTERVAL = range(4)

# 유저의 코인 정보 저장용
user_data = {}

# 로깅 설정
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# 시작 명령어 핸들러
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("안녕하세요! /코인입력 으로 코인을 등록해보세요.")

# 코인 입력 시작
def coin_input(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("코인 이름을 입력해주세요 (예: BTC)")
    return COIN_NAME

def get_coin_name(update: Update, context: CallbackContext) -> int:
    context.user_data["coin"] = update.message.text.upper()
    update.message.reply_text(f"{context.user_data['coin']}의 매수 가격을 입력해주세요.")
    return COIN_PRICE

def get_coin_price(update: Update, context: CallbackContext) -> int:
    try:
        price = float(update.message.text)
        context.user_data["price"] = price
        update.message.reply_text("목표 수익률을 % 단위로 입력해주세요 (예: 10)")
        return TARGET_PROFIT
    except ValueError:
        update.message.reply_text("숫자로 입력해주세요. 매수 가격을 다시 입력해주세요.")
        return COIN_PRICE

def get_target_profit(update: Update, context: CallbackContext) -> int:
    try:
        profit = float(update.message.text)
        context.user_data["profit"] = profit
        update.message.reply_text("알림 간격(초 단위)을 입력해주세요 (예: 60)")
        return INTERVAL
    except ValueError:
        update.message.reply_text("숫자로 입력해주세요. 목표 수익률을 다시 입력해주세요.")
        return TARGET_PROFIT

def get_interval(update: Update, context: CallbackContext) -> int:
    try:
        interval = int(update.message.text)
        coin = context.user_data["coin"]
        user_data[coin] = {
            "price": context.user_data["price"],
            "profit": context.user_data["profit"],
            "interval": interval
        }
        update.message.reply_text(f"{coin} 저장 완료 ✅\n\n/코인입력 으로 다른 코인도 추가 가능해요.")
        return ConversationHandler.END
    except ValueError:
        update.message.reply_text("정수로 입력해주세요. 알림 간격을 다시 입력해주세요.")
        return INTERVAL

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("입력을 취소했습니다.")
    return ConversationHandler.END

def list_coins(update: Update, context: CallbackContext) -> None:
    if not user_data:
        update.message.reply_text("등록된 코인이 없습니다.")
        return
    message = "📊 현재 등록된 코인:\n"
    for coin, info in user_data.items():
        message += f"- {coin}: 매수가 {info['price']}, 목표수익률 {info['profit']}%, 알림간격 {info['interval']}초\n"
    update.message.reply_text(message)

def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        print("TELEGRAM_TOKEN 환경변수를 설정하세요.")
        return

    updater = Updater(token, use_context=True)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('코인입력', coin_input)],
        states={
            COIN_NAME: [MessageHandler(Filters.text & ~Filters.command, get_coin_name)],
            COIN_PRICE: [MessageHandler(Filters.text & ~Filters.command, get_coin_price)],
            TARGET_PROFIT: [MessageHandler(Filters.text & ~Filters.command, get_target_profit)],
            INTERVAL: [MessageHandler(Filters.text & ~Filters.command, get_interval)],
        },
        fallbacks=[CommandHandler('취소', cancel)],
    )

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CommandHandler('코인목록', list_coins))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
