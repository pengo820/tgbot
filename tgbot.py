from dotenv import load_dotenv
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import asyncio

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# 启用日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """发送欢迎消息"""
    await update.message.reply_text('你好，我是AI助手！请直接输入你的问题吧～')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理用户消息"""
    user_input = update.message.text
    
    try:
        # 调用OpenAI API
        resp = requests.post(
            'https://aihubmix.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                "model": "gpt-4.1",
                "messages": [{"role": "user", "content": user_input}],
                "max_tokens": 1024,
                "temperature": 0.7
            },
            timeout=30
        )
        resp.raise_for_status()
        
        result = resp.json()
        reply = result['choices'][0]['message']['content'] if 'choices' in result and result['choices'] else 'AI暂时无法回答，请稍后再试～'
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API调用失败: {e}")
        reply = "抱歉，AI服务暂时无法连接，请稍后再试～"
    except Exception as e:
        logger.error(f"处理消息时出错: {e}")
        reply = "处理消息时出现了错误，请稍后再试～"
    
    await update.message.reply_text(reply)

def main() -> None:
    """启动机器人"""
    # 创建 Application 实例
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # 注册处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # 启动机器人
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()