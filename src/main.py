import os
from dotenv import load_dotenv
from telegram import Bot
import asyncio

load_dotenv()

async def send_test_message():
    bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    await bot.send_message(
        chat_id=chat_id,
        text="JobScanner 测试消息：项目骨架已就位！🚀"
    )
    print("测试消息已发送")

if __name__ == "__main__":
    asyncio.run(send_test_message())