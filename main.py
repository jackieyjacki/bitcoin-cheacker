#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
비트코인·알트코인 가격 모니터링 텔레그램 봇
 - /start              : 봇 소개
 - /코인입력 <심볼>    : 감시할 코인 목록에 추가 (예: /코인입력 BTC)
 - /목표 <심볼> <수익률>: 목표 수익률(%) 설정 (예: /목표 BTC 5)
"""

import os
import logging
import requests
import pytz
from datetime import datetime
from typing import Dict, Any

from telegram import Update, ParseMode
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackContext,
)
from apscheduler.schedulers.background import BackgroundScheduler

# ────────────────────────────────────────────────────────────
# 환경 변수 & 기본 설정
# ────────────────────────────────────────────────────────────
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("환경 변수 TELEGRAM_TOKEN이 설정되지 않았습니다.")

API_URL = "https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"

KST = pytz.timezone("Asia/Seoul")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# {chat_id: {symbol: {"target": float, "last": float}}}
USER_COINS: Dict[int, Dict[str, Dict[str, Any]]] = {}

# ────────────────────────────────────────────────────────────
# 텔레그램 명령어 핸들러
# ────────────────────────────────────────────────────────────
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "📊 안녕하세요! 코인 가격을 모니터링해 드릴게요.\n"
        "`/코인입력 BTC` 처럼 입력해 코인을 등록하고\n"
        "`/목표 BTC 5` 로 목표 수익률(%)도 지정해 보세요.",
        parse_mode=ParseMode.MARKDOWN,
    )


def coin_input(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    if not context.args:
        update.message.reply_text("코인 심볼을 함께 입력해 주세요. 예) /코인입력 BTC")
        return

    symbol = context.args[0].upper()
    USER_COINS.setdefault(chat_id, {})[symbol] = {"target": None, "last": None}
    update.message.reply_text(f"✅ {symbol} 감시를 시작했습니다.")


def set_target(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    if len(context.args) != 2:
        update.message.reply_text("예) /목표 BTC 5  (5 % 수익률)")
        return

    symbol, target_str = context.args
    symbol = symbol.upper()
    try:
        target = float(target_str)
    except ValueError:
        update.message.reply_text("수익률은 숫자로 입력해 주세요.")
        return

    if chat_id not in USER_COINS or symbol not in USER_COINS[chat_id]:
        update.message.reply_text(f"{symbol} 먼저 /코인입력 으로 등록해 주세요.")
        return

    USER_COINS[chat_id][symbol]["target"] = target
    update.message.reply_text(f"🎯 {symbol} 목표 수익률: {target:.2f}% 로 설정")


# ────────────────────────────────────────────────────────────
# 가격 체크 & 알림
# ────────────────────────────────────────────────────────────
def fetch_price(symbol: str) -> float:
    """Binance USDT 페어 가격(USD)을 가져온다."""
    resp = requests.get(API_URL.format(symbol=symbol))
    resp.raise_for_status()
    return float(resp.json()["price"])


def check_prices() -> None:
    """모든 사용자의 등록 코인을 순회하며 알림을 전송."""
    for chat_id, coins in USER_COINS.items():
        for symbol, info in coins.items():
            try:
                price_now = fetch_price(symbol)
            except Exception as e:
                logging.warning("가격 조회 실패: %s", e)
                continue

            last_price = info["last"]
            info["last"] = price_now  # 마지막 가격 갱신

            # 처음 조회라면 기준점만 저장하고 넘어감
            if last_price is None:
                continue

            # 수익률 계산
            change_pct = (price_now - last_price) / last_price * 100

            # 목표 수익률에 근접/도달했는지?
            target = info["target"]
            if target is not None and abs(change_pct) >= target:
                direction = "📈 상승" if change_pct > 0 else "📉 하락"
                context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"{direction}! {symbol}\n"
                        f"현재가: {price_now:,.4f}$\n"
                        f"변동: {change_pct:+.2f}% (목표 {target:+.2f}%)"
                    ),
                )
            # 목표가 없을 땐 5% 이상 변동 시 기본 알림
            elif target is None and abs(change_pct) >= 5:
                context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"⚠️ {symbol} 가격 변동 경고\n"
                        f"현재가: {price_now:,.4f}$\n"
                        f"변동: {change_pct:+.2f}%"
                    ),
                )


# ────────────────────────────────────────────────────────────
# 메인 루틴
# ────────────────────────────────────────────────────────────
def main() -> None:
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("코인입력", coin_input))
    dp.add_handler(CommandHandler("목표", set_target))

    # BackgroundScheduler 는 pytz time-zone 객체가 필요
    scheduler = BackgroundScheduler(timezone=KST)
    scheduler.add_job(check_prices, "interval", minutes=5)
    scheduler.start()
    logging.info("📡 Scheduler started.")

    updater.start_polling()
    logging.info("🤖 Bot started.")
    updater.idle()


if __name__ == "__main__":
    main()
