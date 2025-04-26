import asyncio
import numpy as np
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from googletrans import Translator
from langdetect import detect, LangDetectException
import logging
import requests

from search import find_article
from config import base_url, api_key, folder_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token='7893073484:AAFH_w48fXFfFGYBSo-9Q_z2FJRf6UrCnwY')
dp = Dispatcher()

async def shorten_text(text: str, max_retries=3) -> str:
    if not text.strip():
        return "Текст для сокращения отсутствует"

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {api_key}",
        "Content-Type": "application/json"
    }

    prompt = {
        "modelUri": f"gpt://{folder_id}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": 2000
        },
        "messages": [
            {
                "role": "user",
                "text": f"Привет, максимально сократи этот текст без потери смысла {text}, в ответе просто запиши готовый текст из 5 предложений"
            }
        ]
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=prompt, timeout=10)
            response.raise_for_status()
            return response.json()['result']['alternatives'][0]['message']['text']
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            await asyncio.sleep(1)

    sentences = text.split('.')
    return '. '.join(sentences[:3]) + '.' if len(sentences) > 3 else text

async def check_truthfulness(text: str, max_retries=3) -> str:
    if not text.strip():
        return "Текст для проверки отсутствует"

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {api_key}",
        "Content-Type": "application/json"
    }

    prompt = {
        "modelUri": f"gpt://{folder_id}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": 2000
        },
        "messages": [
            {
                "role": "user",
                "text": f"Проанализируй текст на достоверность: {text}. Ответь только ' Достоверно' или ' Недостоверно', без пояснений"
            }
        ]
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=prompt, timeout=10)
            response.raise_for_status()
            result = response.json()['result']['alternatives'][0]['message']['text']
            if 'достоверно' == result.lower():
                return "Достоверно"
            else:
                return "Недостоверно"
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            await asyncio.sleep(1)

    return "Не удалось проверить достоверность"

def translate_text(text: str, dest_lang='ru') -> str:
    if not text.strip():
        return text

    try:
        translator = Translator()
        return translator.translate(text, dest=dest_lang).text
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return text

@dp.message(Command('start'))
async def start_command(message: types.Message):
    await message.answer("Привет! Я бот-поисковик в базе знаний YouTrack. Введи запрос")

@dp.message()
async def handle_query(message: types.Message):
    try:
        query = message.text.strip()
        if not query:
            return await message.answer("Пожалуйста, введите поисковый запрос")

        try:
            lang = detect(query)
        except LangDetectException:
            lang = 'ru'

        try:
            search_query = translate_text(query, 'ru') if lang != 'ru' else query
            search_mes_id = await message.answer(translate_text('Выполняется поиск, пожалуйста подождите', lang))

            results = find_article(search_query)
            if not results:
                no_results_msg = translate_text("Ничего не найдено. Попробуйте изменить запрос.", lang)
                return await message.answer(no_results_msg)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            error_msg = translate_text("Ошибка поиска. Попробуйте изменить запрос.", lang)
            return await message.answer(error_msg)

        relevant_results = [res for res in results if res[1] > np.float32(0.26)] or results[:3]

        for result in relevant_results[:3]:
            try:
                title, score, content, article_id = result
                if not isinstance(content, str) or not content.strip():
                    content = "Описание недоступно"

                short_content, truthfulness = await asyncio.gather(
                    shorten_text(content),
                    check_truthfulness(content)
                )

                if lang != 'ru':
                    title = translate_text(title, lang)
                    short_content = translate_text(short_content, lang)
                    truthfulness = translate_text(truthfulness, lang)

                link_text = translate_text("Читать полностью", lang)
                reliability_text = translate_text("Оценка достоверности:", lang)

                response = (
                    f"<b>{title}</b>\n\n"
                    f"<i>{short_content}</i>\n\n"
                    f"<b>{reliability_text}</b> {truthfulness}\n\n"
                    f"<a href='{base_url}{article_id}'>{link_text}</a>"
                )

                await message.answer(
                    response,
                    disable_web_page_preview=True,
                    parse_mode='HTML'
                )

            except Exception as e:
                logger.error(f"Error processing result: {e}")
                continue

        await bot.delete_message(message.chat.id, search_mes_id.message_id)
        if not relevant_results:
            no_results_msg = translate_text("Ничего не найдено. Попробуйте изменить запрос.", lang)
            await message.answer(no_results_msg)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        error_msg = translate_text("Произошла ошибка. Пожалуйста, попробуйте другой запрос.", lang)
        await message.answer(error_msg)

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
