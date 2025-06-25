from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import requests
import os

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Render에서 환경변수로 등록 필수

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 명령어 핸들러 함수들 (예시)
def start(update, context):
    update.message.reply_text("Welcome! Use /coin_input to enter coin information.")

def coin_input(update, context):
    update.message.reply_text("Let's enter coin data.")

# 스케줄링 예시 함수
def scheduled_job():
    print("Running scheduled task...")

# 메인 함수
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # 명령어는 영어로!
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("coin_input", coin_input))

    # 스케줄러 예시
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_job, 'interval', minutes=60)
    scheduler.start()

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
