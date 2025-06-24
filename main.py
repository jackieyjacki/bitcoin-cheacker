import os
import json
import logging
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackContext,
    ConversationHandler,
    MessageHandler,
    Filters
)
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

TOKEN = os.environ.get("TELEGRAM_TOKEN")
USER_ID = int(os.envi_
