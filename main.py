
import io, re, time, requests, logging
from PIL import Image
import pytesseract
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler

# === 설정 ===
TOKEN = "7634502846:AAEum3VRV2ZjhspSlJHXgsGsJh-m-KPnodc"
LANG = "kor+eng"
CHECK_INTERVAL = 300  # 5분
DEFAULT_ABOVE_PCT = 0.10
DEFAULT_BELOW_PCT = -0.05

logging.basicConfig(format="%(asctime)s (%(levelname)s) %(message)s", level=logging.INFO)

portfolio = {}
COIN_MAP = {"비트코인": "BTC", "이더리움": "ETH"}

def parse_asset_screen(img_bytes):
    text = pytesseract.image_to_string(Image.open(io.BytesIO(img_bytes)), lang=LANG)
    for kor, ticker in COIN_MAP.items():
        if kor in text:
            m = re.search(rf"{kor}.*?평균매수가[^\d]*([\d,]+).*?보유수량[^\d.]*([\d.]+)", text, re.S)
            if m:
                avg_price = int(m.group(1).replace(",", ""))
                qty = float(m.group(2))
                portfolio[ticker] = portfolio.get(ticker, {})
                portfolio[ticker].update({"qty": qty, "avg": avg_price})
                portfolio[ticker]["above"] = int(avg_price * (1 + DEFAULT_ABOVE_PCT))
                portfolio[ticker]["below"] = int(avg_price * (1 + DEFAULT_BELOW_PCT))

def prettify_portfolio():
    lines = []
    for coin, data in portfolio.items():
        lines.append(f"{coin}: 수량 {data['qty']} / 평균매수 {data['avg']:,}원\n↑알림 {data['above']:,}원  ↓알림 {data['below']:,}원")
    return "\n".join(lines) if lines else "(빈 포트폴리오)"

def photo_handler(update, context):
    photo = update.message.photo[-1]
    file = photo.get_file()
    buf = io.BytesIO()
    file.download(out=buf)
    parse_asset_screen(buf.getvalue())
    update.message.reply_text("✅ 스크린샷 분석 완료!\n" + prettify_portfolio())

def price_check(context):
    chat_id = context.job.context
    for coin, data in portfolio.items():
        try:
            url = f"https://api.bithumb.com/public/ticker/{coin}_KRW"
            price = float(requests.get(url, timeout=10).json()['data']['closing_price'])
            if price >= data['above']:
                context.bot.send_message(chat_id, f"🚀 {coin} {price:,.0f}원 돌파! (+)")
                data['above'] = int(price * (1 + DEFAULT_ABOVE_PCT))
            elif price <= data['below']:
                context.bot.send_message(chat_id, f"📉 {coin} {price:,.0f}원 하락! (-)")
                data['below'] = int(price * (1 + DEFAULT_BELOW_PCT))
        except Exception as e:
            logging.warning(f"{coin} 시세 조회 실패: {e}")

def start(update, context):
    update.message.reply_text("안녕하세요! 자산현황 스크린샷을 보내면\n포트폴리오 등록 + 가격 알림 드릴게요.")

def set_alert(update, context):
    try:
        _, coin, *rest = update.message.text.split()
        if len(rest) == 1:
            value = int(rest[0])
            portfolio[coin]["above"] = value
            update.message.reply_text(f"{coin} ↑알림 {value:,}원 설정 완료!")
        elif len(rest) == 2 and rest[0] in ("above", "below"):
            typ, value = rest
            portfolio[coin]["above" if typ == "above" else "below"] = int(value)
            update.message.reply_text(f"{coin} {typ} {value:,}원 설정 완료!")
    except Exception:
        update.message.reply_text("형식: /setalert BTC 150000000 또는 /setalert BTC below 95000000")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("setalert", set_alert))
    dp.add_handler(MessageHandler(Filters.photo, photo_handler))
    updater.job_queue.run_repeating(price_check, interval=CHECK_INTERVAL, first=10, context=lambda: updater.bot.get_updates()[-1].message.chat.id)
    updater.start_polling()
    logging.info("Bot started.")
    updater.idle()

if __name__ == "__main__":
    main()
