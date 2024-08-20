import telebot
from telebot.custom_filters import StateFilter

import config
from telebot.states.sync.middleware import StateMiddleware
from telebot import types
import keyboards
from telebot.handler_backends import State, StatesGroup
from telebot.states.sync.context import StateContext
import requests
import time
import threading


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class SingletonBot(telebot.TeleBot, metaclass=Singleton):
    def __init__(self, *args, **kwargs):
        TOKEN = config.BOT_TOKEN
        state_storage = telebot.storage.StateRedisStorage(
            host=config.REDIS_HOST, port=config.REDIS_PORT
        )
        super().__init__(
            TOKEN,
            state_storage=state_storage,
            *args,
            parse_mode="HTML",
            use_class_middlewares=True,
            **kwargs,
        )
        self.setup_middleware(StateMiddleware(bot=self))
        self.add_custom_filter(StateFilter(self))
        print('Бот запущен')


bot = SingletonBot()


user_data = {}


COINMARKETCAP_API_URL = "https://pro-api.coinmarketcap.com/v2/tools/price-conversion"


def get_crypto_price(symbol):
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': config.COINMARKETCAP_API_KEY,
    }
    params = {
        'symbol': symbol,
        'amount': 1,
        'convert': 'USD'
    }
    response = requests.get(COINMARKETCAP_API_URL, headers=headers, params=params)
    data = response.json()
    price = data['data'][0]['quote']['USD']['price']
    return price


def check_prices():
    while True:
        for user_id, cryptos in user_data.items():
            for crypto_data in cryptos:
                symbol = crypto_data['crypto']
                current_price = get_crypto_price(symbol)

                if current_price is None:
                    continue  # Если не удалось получить цену, пропускаем эту криптовалюту

                lower_price = crypto_data.get('lower_price', float('inf'))
                higher_price = crypto_data.get('higher_price', float('-inf'))

                if current_price <= lower_price:
                    bot.send_message(user_id, f"Цена {symbol} упала ниже {lower_price}: ${current_price:.2f}")
                elif current_price >= higher_price:
                    bot.send_message(user_id, f"Цена {symbol} превысила {higher_price}: ${current_price:.2f}")

        time.sleep(60)


def start_price_checking():
    threading.Thread(target=check_prices, daemon=True).start()


class CryptoStates(StatesGroup):
    ticker = State()
    lower_price = State()
    higher_price = State()


@bot.message_handler(commands=["start"])
def process_start_command(message: types.Message):
    bot.delete_state(user_id=message.from_user.id)
    bot.send_message(
        chat_id=message.chat.id,
        text="Вас приветствует бот по отслеживанию курсов криптовалют!\n\nЧто вы хотите сделать?",
        reply_markup=keyboards.check_trackers()
    )


@bot.callback_query_handler(func=lambda c: c.data == "add_crypto")
def add_crypto(call: types.CallbackQuery, state: StateContext):
    state.set(CryptoStates.ticker)
    bot.edit_message_text(
        chat_id=call.from_user.id,
        message_id=call.message.id,
        text="Напишите, пожалуйста, тикер криптовалюты, которую хотите добавить"
    )



@bot.message_handler(state=CryptoStates.ticker, content_types=["text"])
def process_ticker(message: types.Message,state: StateContext):
    user_id = message.from_user.id
    crypto = message.text.upper()
    if user_id not in user_data:
        user_data[user_id] = []
    if any(crypto_data['crypto'] == crypto for crypto_data in user_data[user_id]):
        bot.send_message(
            chat_id=message.chat.id,
            text=f"Криптовалюта {crypto} уже отслеживается."
        )
        state.delete()
    else:
        user_data[user_id].append({"crypto": crypto})
        bot.send_message(
            chat_id=message.chat.id,
            text="Напишите, пожалуйста, нижнюю границу цены криптовалюты"
        )
        bot.add_data(user_id=user_id, crypto=crypto)
        state.set(CryptoStates.lower_price)



@bot.message_handler(state=CryptoStates.lower_price)
def process_lower_price(message: types.Message,state: StateContext):
    user_id = message.from_user.id
    try:
        lower_price = float(message.text)
    except ValueError:
        bot.send_message(
            chat_id=message.chat.id,
            text="Пожалуйста, введите корректное числовое значение для нижней границы."
        )
        return
    with bot.retrieve_data(user_id=message.chat.id) as data:
        crypto=data["crypto"]

        # Обновляем данные о нижней границе
    for crypto_data in user_data[user_id]:
        if crypto_data['crypto'] == crypto:
            crypto_data['lower_price'] = lower_price
            break
    bot.send_message(
        chat_id=message.from_user.id,
        text="Напишите, пожалуйста, верхнюю границу цены криптовалюты"
    )
    state.set(CryptoStates.higher_price)


@bot.message_handler(state=CryptoStates.higher_price)
def finish_processing(message: types.Message,state: StateContext):
    user_id = message.from_user.id
    try:
        higher_price = float(message.text)
    except ValueError:
        bot.send_message(
            chat_id=message.chat.id,
            text="Пожалуйста, введите корректное числовое значение для верхней границы."
        )
        return
    with bot.retrieve_data(user_id=message.chat.id) as data:
        crypto = data["crypto"]
        # Обновляем данные о верхней границе
    for crypto_data in user_data[user_id]:
        if crypto_data['crypto'] == crypto:
            crypto_data['higher_price'] = higher_price
            break
    bot.send_message(
        chat_id=message.chat.id,
        text=f"Вы начали отслеживать {crypto} с границами: {user_data[user_id][-1]['lower_price']} - {higher_price}",
        reply_markup=keyboards.check_trackers())
    state.delete()



@bot.callback_query_handler(func=lambda c: c.data == "all_trackers")
def add_crypto(call: types.CallbackQuery):
    user_id = call.from_user.id
    if user_id not in user_data or not user_data[user_id]:
        bot.edit_message_text(
            chat_id=call.from_user.id,
            message_id=call.message.id,
            text="Вы не отслеживаете ни одной криптовалюты.",
            reply_markup=keyboards.start_markup()
        )
        return

    response_message = "Вы отслеживаете следующие криптовалюты:\n"
    for crypto_data in user_data[user_id]:
        crypto = crypto_data.get('crypto')
        lower_price = crypto_data.get('lower_price', 'не задана')
        higher_price = crypto_data.get('higher_price', 'не задана')
        response_message += f"{crypto} - Нижняя граница: {lower_price}, Верхняя граница: {higher_price}\n"

    bot.edit_message_text(
        chat_id=call.from_user.id,
        message_id=call.message.id,
        text=response_message,
        reply_markup=keyboards.start_markup()
    )


start_price_checking()

bot.infinity_polling()
