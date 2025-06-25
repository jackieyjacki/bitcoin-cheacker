import os
import logging
import requests
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)

# ────────────────── 설정 ──────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# 모든 코인 설정을 저장할 딕셔너리
coins = {}
# ────────────────── 핸들러 ──────────────────
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "안녕하세요! ‟/코인입력”으로 코인을 등록하고, "
        "‟/코인목록”으로 현재 설정을 확인할 수 있어요."
    )

def coin_input(update: Update, context: CallbackContext) -> None:
    """사용자: /코인입력 BTC 85000000 0.05"""
    try:
        _, symbol, buy_price, target = update.message.text.split()
        coins[symbol.upper()] = {
            "buy_price": float(buy_price),
            "target": float(target),  # 0.05 → +5 %
        }
        update.message.reply_text(f"{symbol.upper()} 등록 완료 ✅")
    except ValueError:
        update.message.reply_text(
            "사용법: /코인입력 <심볼> <매수가격(KRW)> <목표수익률(0.05=5%)>"
        )

def coin_list(update: Update, context: CallbackContext) -> None:
    if not coins:
        update.message.reply_text("저장된 코인이 없습니다.")
        return
    lines = []
    for sym, info in coins.items():
        lines.append(f"{sym} | 매수 {info['buy_price']:,}₩ | 목표 +{info['target']*100:.1f}%")
    update.message.reply_text("\n".join(lines))

def check_prices(context: CallbackContext) -> None:
    if not coins:
        return
    bot = context.bot
    chat_id = context.job.context
    for sym, info in coins.items():
        price = fetch_price(sym)
        if price is None:
            continue
        pnl = (price - info["buy_price"]) / info["buy_price"]
        msg = f"[{sym}] 현재가 {price:,}₩ | 손익 {pnl*100:+.2f}%"
        bot.send_message(chat_id, msg)

def fetch_price(symbol: str):
    """업비트 KRW 마켓 가격 가져오기 (간단 요청)"""
    url = f"https://api.upbit.com/v1/ticker?markets=KRW-{symbol.upper()}"
    try:
        r = requests.get(url, timeout=3)
        r.raise_for_status()
        return r.json()[0]["trade_price"]
    except Exception as e:
        logger.warning("가격 조회 실패 %s: %s", symbol, e)
        return None

# ────────────────── 메인 ──────────────────
def main() -> None:
    token = os.getenv("TOKEN")            # ← **딱 한 번만 읽음**
    if not token:
        raise RuntimeError("TOKEN 환경변수가 없습니다!")

    updater = Updater(token=token, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("코인입력", coin_input))
    dp.add_handler(CommandHandler("코인목록", coin_list))

    # 60초마다 가격 체크
    job_queue = updater.job_queue
    job_queue.run_repeating(check_prices, interval=60, first=10, context=updater.bot.id)

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
