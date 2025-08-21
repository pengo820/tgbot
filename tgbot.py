from dotenv import load_dotenv
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import asyncio
from typing import List, Dict

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# 启用日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========= 可调参数 =========
# 保留的历史消息最大条数（role+content 为一条；约等于 N/2 轮对话）
HISTORY_MAX_MESSAGES = 24
# 可选：系统提示词，给模型稳定角色与风格
SYSTEM_PROMPT = "You are a helpful, concise, and practical assistant."
# ==========================

def _get_history(context: ContextTypes.DEFAULT_TYPE) -> List[Dict[str, str]]:
    """获取当前 chat 的上下文历史（list[{'role','content'}]）"""
    return context.chat_data.setdefault("history", [])

def _trim_history(history: List[Dict[str, str]], max_messages: int = HISTORY_MAX_MESSAGES) -> None:
    """按条数裁剪历史，保留最近 max_messages 条"""
    if len(history) > max_messages:
        del history[:-max_messages]

def _build_messages(user_input: str, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """将系统提示词 + 历史 + 当前用户消息 拼成 API 所需 messages"""
    messages: List[Dict[str, str]] = []
    if SYSTEM_PROMPT:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})
    messages.extend(history)
    messages.append({"role": "user", "content": user_input})
    return messages

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """发送欢迎消息，同时不清空历史（便于再次 /start 后继续）"""
    await update.message.reply_text('你好，我是AI助手！请直接输入你的问题吧～\n'
                                    '提示：发送 /clear 可清空本聊天的对话记忆。')

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """清空当前 chat 的上下文"""
    context.chat_data["history"] = []
    await update.message.reply_text("已清空本聊天的对话记忆（context）。")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理用户消息（带上下文）"""
    user_input = update.message.text

    # 取出并裁剪历史
    history = _get_history(context)
    _trim_history(history, HISTORY_MAX_MESSAGES)

    # 组装消息
    messages = _build_messages(user_input, history)

    try:
        # 调用 OpenAI 兼容 API（aihubmix）
        resp = requests.post(
            'https://aihubmix.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                "model": "gpt-4.1",
                "messages": messages,
                "max_tokens": 1024,
                "temperature": 0.7
            },
            timeout=30
        )
        resp.raise_for_status()

        result = resp.json()
        reply = (result.get('choices') or [{}])[0].get('message', {}).get('content')
        if not reply:
            reply = 'AI暂时无法回答，请稍后再试～'

        # —— 更新本地上下文（先存用户，再存助理）——
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": reply})
        _trim_history(history, HISTORY_MAX_MESSAGES)

    except requests.exceptions.RequestException as e:
        logger.error(f"API调用失败: {e}")
        reply = "抱歉，AI服务暂时无法连接，请稍后再试～"
    except Exception as e:
        logger.error(f"处理消息时出错: {e}")
        reply = "处理消息时出现了错误，请稍后再试～"

    await update.message.reply_text(reply)

def main() -> None:
    """启动机器人"""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # 注册处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 启动机器人
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if name == "__main__":
    main()
