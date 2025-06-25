#!/usr/bin/env python3
# main.py
import logging, os, re, requests, pytz
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update, ParseMode
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext
)

# ──────────────────────────────────────────────────────────────
# 1. 기본 설정
# ──────────────────────────────────────────────────────────────
TOKEN = os.getenv("TELEGRAM_TOKEN")          # Render 환경변수에 저장
ADMIN = int(os.getenv("ADMIN_ID", "0"))      # (선택) 관리자 챗 ID
TIMEZONE = pytz.timezone("Asia/Seoul")       # 서울 시간

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO
)

# 코인 정보 저장용
coins = {}          # { "BTC": {"buy": 1000000, "target": 5.0} , ... }

# ──────────────────────────────────────────────────────────────
# 2. 헬퍼 함수
# ──────────────────────────────────────────────────────────────
def price_usdt(symbol: str) -> float:
    """Binance 현물 USDT 가격을 가져온다 (예: BTC → BTCUSDT)."""
    url = f"https://api.binance.com/api/v3/ticker/price"
    r = requests.get(url, params={"symbol": f"{symbol.upper()}USDT"}, timeout=8)
    r.raise_for_status()
    return float(r.json()["price"])

def emoji_pct(p: float) -> str:
    return "📈" if p >= 0 else "📉"

# ──────────────────────────────────────────────────────────────
# 3. 명령어 핸들러
# ──────────────────────────────────────────────────────────────
def cmd_start(update: Update, _: CallbackContext):
    msg = (
        "🪙 *Crypto Watch Bot*\n\n"
        "`/addcoin  BTC 72000000`  – 매수 등록 (가격은 원화)\n"
        "`/settarget BTC 5`        – 목표 수익률(%) 설정\n"
        "`/removecoin BTC`         – 코인 삭제\n"
        "`/status`                 – 현황 보기"
    )
    update.message.reply_markdown(msg)

def cmd_addcoin(update: Update, _: CallbackContext):
    try:
        _, sym, buy = update.message.text.split()
        coins[sym.upper()] = {"buy": float(buy), "target": None}
        update.message.reply_text(f"✅ Added {sym.upper()} @ {buy} KRW")
    except Exception:
        update.message.reply_text("❌ 사용법: /addcoin  BTC  72000000")

def cmd_settarget(update: Update, _: CallbackContext):
    try:
        _, sym, tgt = update.message.text.split()
        sym = sym.upper()
        if sym not in coins:
            update.message.reply_text("❌ 먼저 /addcoin 으로 등록하세요")
            return
        coins[sym]["target"] = float(tgt)
        update.message.reply_text(f"🎯 {sym} 목표 수익률을 {tgt}% 로 설정")
    except Exception:
        update.message.reply_text("❌ 사용법: /settarget  BTC  5")

def cmd_removecoin(update: Update, _: CallbackContext):
    try:
        _, sym = update.message.text.split()
        if coins.pop(sym.upper(), None):
            update.message.reply_text(f"🗑️ {sym.upper()} 삭제")
        else:
            update.message.reply_text("⚠️ 등록되지 않은 코인입니다")
    except Exception:
        update.message.reply_text("❌ 사용법: /removecoin  BTC")

def cmd_status(update: Update, _: CallbackContext):
    if not coins:
        update.message.reply_text("📭 등록된 코인이 없습니다")
        return
    lines = []
    for s, info in coins.items():
        now = price_usdt(s) * 1400  # 간단히 1 USDT≈₩1,400 가정
        diff_pct = (now - info["buy"]) / info["buy"] * 100
        tgt_txt = f" / target {info['target']}%" if info["target"] is not None else ""
        lines.append(f"{emoji_pct(diff_pct)} *{s}* {now:,.0f}₩  ({diff_pct:+.2f}%){tgt_txt}")
    update.message.reply_markdown("\n".join(lines))

# ──────────────────────────────────────────────────────────────
# 4. 가격 체크 주기 작업
# ──────────────────────────────────────────────────────────────
def check_prices():
    if not coins or not ADMIN:
        return
    for s, info in coins.items():
        now = price_usdt(s) * 1400
        diff_pct = (now - info["buy"]) / info["buy"] * 100
        # 목표 수익률 근접 – 5%p 이내일 때 알림
        tgt = info.get("target")
        if tgt is not None and abs(diff_pct - tgt) <= 5:
            text = (
                f"{emoji_pct(diff_pct)} *{s}* 현 수익률 {diff_pct:+.2f}% \n"
                f"목표 {tgt}% 에 근접!"
            )
            updater.bot.send_message(ADMIN, text, parse_mode=ParseMode.MARKDOWN)

# ──────────────────────────────────────────────────────────────
# 5. 메인 루틴
# ──────────────────────────────────────────────────────────────
def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN 환경변수가 설정되지 않았습니다!")

    global updater
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start",     cmd_start))
    dp.add_handler(CommandHandler("addcoin",   cmd_addcoin))
    dp.add_handler(CommandHandler("settarget", cmd_settarget))
    dp.add_handler(CommandHandler("removecoin",cmd_removecoin))
    dp.add_handler(CommandHandler("status",    cmd_status))

    # 백그라운드 스케줄러
    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    scheduler.add_job(check_prices, "interval", minutes=5)
    scheduler.start()

    logging.info("Bot started")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
