from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup



def start_markup() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(text="Добавить отслеживание новой криптовалюты", callback_data="add_crypto"),
    )
    return markup

def check_trackers() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(text="Добавить отслеживание новой криптовалюты", callback_data="add_crypto"),
    )
    markup.add(
        InlineKeyboardButton(text="Посмотреть мои трекеры", callback_data="all_trackers"),
    )
    return markup