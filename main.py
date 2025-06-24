import logging
import os
import requests
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from PIL import Image
import pytesseract
from io import BytesIO

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    TOKEN = "여기에_네_봇_토큰_직접_넣어도_됨"

# 로깅 설정
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# 가격 API (업비트 기준)
def get_price(symbol):
    try:
        url = f"https://api.upbit.com/v1/ticker?markets={symbol}"
        res = requests.get(url)
        data = res.json()[0]
        return data['trade_price']
    except Exception as e:
        return None

# 사진 처리
def handle_photo(update: Update, context: CallbackContext):
    file = update.message.photo[-1].get_file()
    img_bytes = BytesIO()
    file.download(out=img_bytes)
    img_bytes.seek(0)

    try:
        image = Image.open(img_bytes)
        text = pytesseract.image_to_string(image, lang='kor+eng')

        result = parse_crypto_info(text)
        update.message.reply_text(result)

    except Exception as e:
        update.message.reply_text("이미지 분석에 실패했습니다.")

# OCR 결과에서 코인, 매수금액 추출 (기초 버전)
def parse_crypto_info(text):
    lines = text.split("\n")
    output = []
    for line in lines:
        if any(token in line.lower() for token in ["btc", "eth", "sol", "xrp", "doge", "matic"]):
            try:
                name = line.split()[0].upper()
                parts = line.split()
                for p in parts:
                    if "원" in p or p.replace(",", "").isdigit():
                        buy_price = ''.join(filter(str.isdigit, p))
                        price = get_price("KRW-" + name)
                        if price:
                            diff = price - int(buy_price)
                            rate = (diff / int(buy_price)) * 100
                            msg = f"{name} 현재가: {price:,.0f}원\n매수가: {int(buy_price):,}원\n수익률: {rate:+.2f}%"
                            output.append(msg)
                        break
            except:
                continue
    return "\n\n".join(output) if output else "코인 정보를 찾지 못했어요."

# /start 명령어
def start(update: Update, context: CallbackContext):
    update.message.reply_text("📈 자산현황 스크린샷을 보내주면 분석해줄게요!")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.photo, handle_photo))

    updater.start_polling()
    logging.info("✅ Bot started.")
    updater.idle()

if __name__ == '__main__':
    main()
