import asyncio
import logging
import os
import signal
import sys
from collections import deque
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from telegram import Bot
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder

# .env dan token va kanal ID ni yuklash
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# WebDriver sozlash
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=chrome_options)

def get_emoji_for_coeff(coeff):
    try:
        coeff = float(str(coeff).lower().replace('x', '').replace(',', '.'))
        if coeff <= 0:
            return "⚪"
        elif coeff < 2.0:
            return "🔵"  # Ko'k
        elif coeff < 10.0:
            return "🟣"  # Binafsha
        elif coeff < 20.0:
            return "🟡"  # Sariq
        else:
            return "🔴"  # Qizil
    except (ValueError, TypeError):
        return "⚪"  # Noto'g'ri format

async def main():
    application = ApplicationBuilder().token(TOKEN).build()
    bot = Bot(token=TOKEN)

    message_ids = deque()
    last_sent_result = None
    MAX_MESSAGES = 20
    DELETE_COUNT = 5

    logger.info("🚀 Bot ishga tushdi")

    async def send_result_message(result):
        nonlocal message_ids, last_sent_result
        
        if not result or result == last_sent_result:
            return

        emoji = get_emoji_for_coeff(result)
        
        try:
            coeff = float(str(result).lower().replace('x', '').replace(',', '.'))
            fire_emoji = " 🔥" if coeff >= 20.0 else ""
        except:
            fire_emoji = ""

        message_text = (
            f"🎯 Yangi o'yin natijasi: {emoji}\n\n"
            f"<b>{result}{fire_emoji}</b>"
        )

        try:
            msg = await bot.send_message(
                chat_id=CHANNEL_ID,
                text=message_text,
                parse_mode=ParseMode.HTML
            )
            message_ids.append(msg.message_id)
            last_sent_result = result
            logger.info(f"✅ Xabar yuborildi: {result} {emoji}")

            # Eski xabarlarni tozalash
            if len(message_ids) > MAX_MESSAGES:
                for _ in range(DELETE_COUNT):
                    if message_ids:
                        old_id = message_ids.popleft()
                        try:
                            await bot.delete_message(chat_id=CHANNEL_ID, message_id=old_id)
                            logger.info(f"🗑 Xabar o'chirildi: {old_id}")
                        except Exception as e:
                            logger.warning(f"⚠️ Xabar o'chirilmadi: {e}")

        except Exception as e:
            logger.error(f"❌ Xabar yuborishda xato: {e}")

    async def monitor_results():
        while True:
            try:
                driver.refresh()
                await asyncio.sleep(5)  # Sahifa yuklanishini kutish

                result_element = driver.find_element(By.ID, "history-item-1")
                current_result = result_element.text.strip()
                
                await send_result_message(current_result)
                await asyncio.sleep(10)  # Yangilanish oralig'i

            except Exception as e:
                logger.error(f"❌ Monitorlikda xato: {str(e)}")
                await asyncio.sleep(30)  # Xato bo'lganda kutish vaqti

    def shutdown(signum, frame):
        logger.info("🛑 Bot to'xtatilmoqda...")
        driver.quit()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        driver.get("https://100hp.app/lucky/onewin/")
        await asyncio.sleep(5)  # Birinchi yuklanish uchun kutish
        await monitor_results()
    except Exception as e:
        logger.critical(f"💀 Kritik xato: {str(e)}")
        driver.quit()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
