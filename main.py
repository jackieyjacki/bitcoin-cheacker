import logging
import pytz
import requests
import json
import time
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler

# 로깅 설정
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# 봇 토큰
TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'

# 유저별 코인 정보 저장용 딕셔너리
user_data = {}

# 가격 확인 함수 (예시: 업비트 API 사용)
def get_price(symbol):
    try:
        url = f'https://api.upbit.com/v1/ticker?markets={symbol}'
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data[0]['trade_price']
        else:
            return None
    except Exception as e:
        logging.error(f"가격 조회 오류: {e}")
        return None

# 가격 체크 및 알림
def check_prices():
    for user_id, coins in user_data.items():
        for coin, info in coins.items():
            current_price = get_price(info['symbol'])
            if current_price:
                rate = (current_price - info['buy_price']) / info['buy_price'] * 100
                logging.info(f"[{user_id}] {coin} 수익률: {rate:.2f}%")

                # 메시지 조건별 출력
                if rate >= info['target']:
                    message = f"🎯 {coin} 목표 도달!\n현재가: {current_price}원\n수익률: {rate:.2f}%"
                elif rate > 0:
                    message = f"📈 {coin} 상승 중!\n현재가: {current_price}원\n수익률: {rate:.2f}%"
                elif rate < 0:
                    message = f"📉 {coin} 하락 중!\n현재가: {current_price}원\n수익률: {rate:.2f}%"
                else:
                    message = f"{coin} 현재가: {current_price}원 (변동 없음)"

                # 실제 메시지 보내기
                context = user_data[user_id].get('context')
                if context:
                    context.bot.send_message(chat_id=user_id, text=message)

# /코인입력 명령어 처리
def start_coin_input(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data[user_id] = {'context': context}
    update.message.reply_text("📌 코인 입력을 시작합니다.\n예: BTC KRW기준이면 'KRW-BTC' 형식으로 입력하세요.")

    # 여기에 이어서 매수가, 목표 수익률 등 인터랙션 추가 가능
    # 코드를 간결히 유지하기 위해 생략함

# 봇 실행 함수
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("코인입력", start_coin_input))

    # 스케줄러 시작 (UTC 기준)
    scheduler = BackgroundScheduler(timezone=pytz.utc)
    scheduler.add_job(check_prices, "interval", seconds=60)
    scheduler.start()

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
