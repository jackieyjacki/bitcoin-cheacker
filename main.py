import logging
import os
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

ASK_COIN, ASK_PRICE, ASK_TARGET, ASK_INTERVAL = range(4)
user_data_store = {}

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "📈 안녕하세요! 비트코인 수익률 알림 봇입니다.\n\n"
        "/coininput 으로 코인을 등록하고\n"
        "/coinupdate 으로 수정을,\n"
        "/coindelete 으로 삭제할 수 있습니다."
    )

def coin_input(update: Update, context: CallbackContext):
    update.message.reply_text("💰 코인 이름을 입력해주세요 (예: BTC, ETH)")
    return ASK_COIN

def ask_price(update: Update, context: CallbackContext):
    context.user_data['coin'] = update.message.text.upper()
    update.message.reply_text("🪙 매수 가격을 입력해주세요 (숫자만)")
    return ASK_PRICE

def ask_target(update: Update, context: CallbackContext):
    try:
        context.user_data['price'] = float(update.message.text)
    except ValueError:
        update.message.reply_text("❗ 숫자로 입력해주세요.")
        return ASK_PRICE
    update.message.reply_text("🎯 목표 수익률을 %로 입력해주세요 (예: 10)")
    return ASK_TARGET

def ask_interval(update: Update, context: CallbackContext):
    try:
        context.user_data['target'] = float(update.message.text)
    except ValueError:
        update.message.reply_text("❗ 숫자로 입력해주세요.")
        return ASK_TARGET
    update.message.reply_text("⏱️ 알림 간격(초)을 입력해주세요")
    return ASK_INTERVAL

def save_coin(update: Update, context: CallbackContext):
    try:
        interval = int(update.message.text)
    except ValueError:
        update.message.reply_text("❗ 숫자로 입력해주세요.")
        return ASK_INTERVAL

    context.user_data['interval'] = interval
    user_id = update.effective_user.id

    if user_id not in user_data_store:
        user_data_store[user_id] = []

    user_data_store[user_id].append(context.user_data.copy())

    update.message.reply_text(
        f"✅ 저장 완료!\n\n"
        f"코인: {context.user_data['coin']}\n"
        f"매수가: {context.user_data['price']}\n"
        f"목표 수익률: {context.user_data['target']}%\n"
        f"알림 간격: {context.user_data['interval']}초"
    )
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("🚫 입력이 취소되었습니다.")
    return ConversationHandler.END

def coin_update(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in user_data_store or not user_data_store[user_id]:
        update.message.reply_text("❗ 저장된 코인이 없습니다.")
        return

    reply = "✏️ 수정할 코인을 선택해주세요:\n"
    for i, coin in enumerate(user_data_store[user_id]):
        reply += f"{i + 1}. {coin['coin']}\n"
    update.message.reply_text(reply)
    context.user_data['update_mode'] = True

def coin_delete(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in user_data_store or not user_data_store[user_id]:
        update.message.reply_text("❗ 삭제할 코인이 없습니다.")
        return

    reply = "❌ 삭제할 코인을 선택해주세요:\n"
    for i, coin in enumerate(user_data_store[user_id]):
        reply += f"{i + 1}. {coin['coin']}\n"
    update.message.reply_text(reply)
    context.user_data['delete_mode'] = True

def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        print("TELEGRAM_TOKEN 환경변수를 설정하세요.")
        return

    updater = Updater(token, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("coininput", coin_input)],
        states={
            ASK_COIN: [MessageHandler(Filters.text & ~Filters.command, ask_price)],
            ASK_PRICE: [MessageHandler(Filters.text & ~Filters.command, ask_target)],
            ASK_TARGET: [MessageHandler(Filters.text & ~Filters.command, ask_interval)],
            ASK_INTERVAL: [MessageHandler(Filters.text & ~Filters.command, save_coin)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler("coinupdate", coin_update))
    dp.add_handler(CommandHandler("coindelete", coin_delete))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
