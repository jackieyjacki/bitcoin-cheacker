import logging
import os
import requests
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters
from apscheduler.schedulers.background import BackgroundScheduler

# 로깅 설정
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 코인 정보 저장용 딕셔너리
coin_data = {}

# 기본 봇 토큰 (배포 환경에서는 환경변수로 관리)
TOKEN = os.environ.get("TELEGRAM_TOKEN", "여기에_실제_토큰_값_입력")

# 명령어: /start
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('안녕하세요! 코인 수익률 알림 봇입니다.\n"/coininput"으로 코인을 등록하세요.')

# 명령어: /coininput (코인 입력)
def coin_input(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('코인 이름을 입력해주세요.')
    return

# 명령어: /coinlist (현재 설정 확인)
def coin_list(update: Update, context: CallbackContext) -> None:
    if not coin_data:
        update.message.reply_text('등록된 코인이 없습니다.')
    else:
        message = "현재 등록된 코인:\n"
        for name, info in coin_data.items():
            message += f"- {name}: 매수가 {info['buy_price']}, 목표 수익률 {info['target_profit']}%\n"
        update.message.reply_text(message)

# 가격 확인용 함수 (예시)
def check_prices():
    for name, info in coin_data.items():
        try:
            response = requests.get(f"https://api.upbit.com/v1/ticker?markets=KRW-{name}")
            response.raise_for_status()
            data = response.json()[0]
            current_price = data['trade_price']
            profit = (current_price - info['buy_price']) / info['buy_price'] * 100
            logger.info(f"{name}: 현재가 {current_price}, 수익률 {profit:.2f}%")
        except Exception as e:
            logger.error(f"가격 확인 실패: {name}, 오류: {e}")

# 메인 함수
def main():
    print(f"=== TOKEN 값: {TOKEN} ===")

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("coininput", coin_input))
    dp.add_handler(CommandHandler("coinlist", coin_list))

    # 주기적으로 가격 확인
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_prices, 'interval', minutes=5)
    scheduler.start()

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
