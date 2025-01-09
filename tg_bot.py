import re
import random
import telegram

from environs import Env
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler

from redis_db import r
from questions_and_answers import logger, questions_and_answers


env = Env()
env.read_env()
tg_bot_token = env.str('TG_BOT_TOKEN')

QUESTION, ANSWER = range(2)

reply_markup = telegram.ReplyKeyboardMarkup([['Новый вопрос', 'Сдаться'], ['Мой счет']])


def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user

    chat_id = str(update.effective_chat.id)
    update.message.reply_markdown_v2(
        fr'Привет\! {user.mention_markdown_v2()}',
        reply_markup=reply_markup
    )
    context.bot.send_message(chat_id=chat_id,
                     text='Нажмите "Новый вопрос" для начала викторины\n/cansel-для отмены',
                     reply_markup=reply_markup)

    r.set(f"user:{chat_id}:score", "0")
    return QUESTION


def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


def end(update: Update, context: CallbackContext):
    update.message.reply_text("Викторина завершена. Для начала новой викторины введите /start")
    return ConversationHandler.END


def handle_new_question_request(update: Update, context: CallbackContext) -> None:
    """Handles request for a new question."""
    chat_id = str(update.effective_chat.id)
    question = random.choice(list(questions_and_answers.keys()))
    print(f'вопрос:{question}')
    print(f'ответ:{questions_and_answers[question]}')
    r.set(f"user:{chat_id}:current_question", question)
    context.bot.send_message(chat_id=chat_id, text=question, reply_markup=reply_markup)

    return ANSWER


def handle_solution_attempt(update: Update, context: CallbackContext) -> None:
    """Handles user's attempt to answer a question."""
    chat_id = str(update.effective_chat.id)
    user_text = update.message.text
    user_answer = re.search(r'^[^.]+', user_text).group().lower().strip()
    current_question = r.get(f"user:{chat_id}:current_question")
    correct_answer = questions_and_answers[current_question]
    smart_correct_answer = re.search(r'^[^(^.]+', correct_answer).group().lower().strip().strip("'\"")

    if user_answer == smart_correct_answer:
        context.bot.send_message(chat_id=chat_id,
                                 text='Правильно! Поздравляю! Для следующего вопроса нажми "Новый вопрос"',
                                 reply_markup=reply_markup)
        score = int(r.get(f"user:{chat_id}:score"))
        r.set(f"user:{chat_id}:score", str(score+1))
        return QUESTION
    else:
        context.bot.send_message(chat_id=chat_id,
                                 text=f'Неправильно… Попробуешь ещё раз?',
                                 reply_markup=reply_markup)

        return ANSWER


def handle_solution_give_up(update: Update, context: CallbackContext) -> None:
    """Handles user giving up on a question."""
    chat_id = str(update.effective_chat.id)
    current_question = r.get(f"user:{chat_id}:current_question")
    correct_answer = questions_and_answers[current_question]
    context.bot.send_message(chat_id=chat_id,
                            text=f'Правильный ответ: {correct_answer}. Для следующего вопроса нажми "Новый вопрос"',
                            reply_markup=reply_markup)
    return QUESTION


def show_score(update: Update, context: CallbackContext) -> None:
    """Shows user's current score."""
    chat_id = str(update.effective_chat.id)
    score = r.get(f"user:{chat_id}:score")
    context.bot.send_message(chat_id=chat_id, text=f'Ваш счет: {score}', reply_markup=reply_markup)
    return ANSWER


def main() -> None:
    try:
        updater = Updater(tg_bot_token)
        dispatcher = updater.dispatcher

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],

            states={
                QUESTION: [MessageHandler(Filters.regex('^Новый вопрос$'), handle_new_question_request),
                           MessageHandler(Filters.regex('^Мой счет$'), show_score)],
                ANSWER:
                    [MessageHandler(
                    Filters.text & ~Filters.command & ~Filters.regex('^Новый вопрос$') & ~Filters.regex('^Сдаться$') & ~Filters.regex('^Мой счет$'),
                        handle_solution_attempt),
                    MessageHandler(Filters.regex('^Сдаться$'), handle_solution_give_up),
                    MessageHandler(Filters.regex('^Новый вопрос$'), handle_new_question_request),
                    MessageHandler(Filters.regex('^Мой счет$'), show_score)]

            },

            fallbacks=[CommandHandler('cansel', end)]
        )

        dispatcher.add_handler(conv_handler)

        updater.start_polling()
        updater.idle()
    except Exception as er:
        logger.exception(f'Ошибка {er}')

if __name__ == '__main__':
    main()
