import os
import random
import string
import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher.filters.state import State, StatesGroup
import aiohttp

API_TOKEN = 'ТГ ТОКЕН'
API_KEY = 'ЛОЛЗ ТОКЕН'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

user_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
user_keyboard.add(KeyboardButton("Создать платеж"))
user_keyboard.add(KeyboardButton("Проверить платеж"))

payments = {}

#5680221 айди мой смени на свой. 
def generate_payment_link(amount: int = 1, comment: str = None) -> tuple:
    if comment is None:
        comment = f"QIYANA-{''.join(random.choices(string.ascii_lowercase + string.digits, k=20))}"
    return f"https://lolz.live/payment/balance/transfer?user_id=5680221&amount={amount}&currency=rub&comment={comment}&transfer_hold=false", comment


async def check_payment(comment: str, amount: int) -> dict:
    url = f"https://api.lzt.market/user/payments?type=income&pmin={amount}&pmax={amount}&comment={comment}&is_hold=false"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {API_KEY}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            data = await response.json()
            logging.info(f"Полученные данные от API: {data}")

    payments_data = data.get('payments', {})
    logging.info(f"Найденные платежи: {payments_data}")

    if payments_data:
        for payment_id, payment_data in payments_data.items():
            payment_comment = payment_data['data'].get('comment', '')
            payment_amount = payment_data.get('incoming_sum', 0)
            is_hold = payment_data.get('is_hold', 0)
            payment_status = payment_data.get('payment_status', '')

            logging.info(
                f"Проверяем платеж: сумма {payment_amount}, комментарий {payment_comment}, статус {payment_status}")

            if payment_comment == comment and payment_amount == amount:
                return {
                    'found': True,
                    'amount_match': True,
                    'comment_match': True,
                    'is_hold': is_hold == 1,
                    'status': payment_status
                }
    return {'found': False}


class PaymentStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_comment = State()


@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.reply("Привет! Выберите действие:", reply_markup=user_keyboard)


@dp.message_handler(Text(equals="Создать платеж"))
async def create_payment(message: types.Message):
    await message.reply("Введите сумму платежа:")
    await PaymentStates.waiting_for_amount.set()


@dp.message_handler(state=PaymentStates.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        link, comment = generate_payment_link(amount)
        payments[message.from_user.id] = {'amount': amount, 'comment': comment, 'created_at': datetime.now()}

        await message.reply(f"Ссылка на платеж: {link}\nКомментарий: {comment}",
                            reply_markup=user_keyboard)
        await state.finish()
    except ValueError:
        await message.reply("Пожалуйста, введите корректную сумму.")


@dp.message_handler(Text(equals="Проверить платеж"))
async def check_payment_handler(message: types.Message):
    payment_info = payments.get(message.from_user.id)

    if not payment_info:
        await message.reply("Сначала создайте платеж, нажав кнопку 'Создать платеж'.",
                            reply_markup=user_keyboard)
        return

    if datetime.now() - payment_info['created_at'] > timedelta(minutes=10):
        await message.reply("Ссылка на платеж аннулирована. Создайте новый платеж.",
                            reply_markup=user_keyboard)
        payments.pop(message.from_user.id)
        return

    result = await check_payment(payment_info['comment'], payment_info['amount'])

    if result['found']:
        if result['amount_match'] and result['comment_match']:
            if result['is_hold']:
                await message.reply("Платеж найден, но находится в холде.",
                                    reply_markup=user_keyboard)
            else:
                await message.reply(
                    f"Платеж успешно получен и не находится в холде!\nКомментарий: {payment_info['comment']}",
                    reply_markup=user_keyboard)
                payments.pop(message.from_user.id)
        else:
            await message.reply("Платеж найден, но параметры не совпадают (сумма или комментарий неверны).",
                                reply_markup=user_keyboard)
    else:
        await message.reply("Платеж не найден.",
                            reply_markup=user_keyboard)


async def main():
    await dp.start_polling()


if __name__ == '__main__':
    asyncio.run(main())