import logging
import random
import re
import redis
import telegram

from environs import Env
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler

from quiz_data_parser import get_questions_and_answers

logger = logging.getLogger(__name__)


QUESTION, ANSWER = range(2)


def start(update: Update, context: CallbackContext, redis_db, reply_markup) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user

    chat_id = update.effective_chat.id
    update.message.reply_markdown_v2(
        fr'Привет\! {user.mention_markdown_v2()}',
        reply_markup=reply_markup
    )
    context.bot.send_message(chat_id=chat_id,
                     text='Нажмите "Новый вопрос" для начала викторины\n/cansel-для отмены',
                     reply_markup=reply_markup)

    redis_db.set(f"user:{chat_id}:score", "0")
    return QUESTION


def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


def end(update: Update, context: CallbackContext):
    update.message.reply_text("Викторина завершена. Для начала новой викторины введите /start")
    return ConversationHandler.END


def handle_new_question_request(update: Update, context: CallbackContext, redis_db, reply_markup, questions_and_answers) -> None:
    """Handles request for a new question."""
    chat_id = update.effective_chat.id
    question = random.choice(list(questions_and_answers.keys()))
    redis_db.set(f"user:{chat_id}:current_question", question)
    context.bot.send_message(chat_id=chat_id, text=question, reply_markup=reply_markup)

    return ANSWER


def handle_solution_attempt(update: Update, context: CallbackContext, redis_db, reply_markup, questions_and_answers) -> None:
    """Handles user's attempt to answer a question."""
    chat_id = update.effective_chat.id
    user_text = update.message.text
    user_answer = re.search(r'^[^.]+', user_text).group().lower().strip()
    current_question = redis_db.get(f"user:{chat_id}:current_question")
    correct_answer = questions_and_answers[current_question]
    smart_correct_answer = re.search(r'^[^(^.]+', correct_answer).group().lower().strip().strip("'\"")

    if user_answer == smart_correct_answer:
        context.bot.send_message(chat_id=chat_id,
                                 text='Правильно! Поздравляю! Для следующего вопроса нажми "Новый вопрос"',
                                 reply_markup=reply_markup)
        score = int(redis_db.get(f"user:{chat_id}:score"))
        redis_db.set(f"user:{chat_id}:score", str(score+1))
        return QUESTION
    else:
        context.bot.send_message(chat_id=chat_id,
                                 text=f'Неправильно… Попробуешь ещё раз?',
                                 reply_markup=reply_markup)

        return ANSWER


def handle_solution_give_up(update: Update, context: CallbackContext, redis_db, reply_markup, questions_and_answers) -> None:
    """Handles user giving up on a question."""
    chat_id = update.effective_chat.id
    current_question = redis_db.get(f"user:{chat_id}:current_question")
    correct_answer = questions_and_answers[current_question]
    context.bot.send_message(chat_id=chat_id,
                            text=f'Правильный ответ: {correct_answer}. Для следующего вопроса нажми "Новый вопрос"',
                            reply_markup=reply_markup)
    return QUESTION


def show_score(update: Update, context: CallbackContext, redis_db, reply_markup) -> None:
    """Shows user's current score."""
    chat_id = update.effective_chat.id
    score = redis_db.get(f"user:{chat_id}:score")
    context.bot.send_message(chat_id=chat_id, text=f'Ваш счет: {score}', reply_markup=reply_markup)
    return ANSWER


def main() -> None:
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
    )
    logger.setLevel(logging.DEBUG)

    reply_markup = telegram.ReplyKeyboardMarkup([['Новый вопрос', 'Сдаться'], ['Мой счет']])
    env = Env()
    env.read_env()
    questions_file_name = env.str('QUESTIONS_FILE', '1vs1200.txt')
    tg_bot_token = env.str('TG_BOT_TOKEN')
    redis_host = env.str('REDIS_HOST')
    redis_port = env.str('REDIS_PORT')
    redis_password = env.str('REDIS_PASSWORD')
    try:
        questions_and_answers = get_questions_and_answers(questions_file_name)
        redis_db = redis.StrictRedis(
            host=redis_host,
            port=redis_port,
            decode_responses=True,
            charset="utf-8",
            password=redis_password,
        )

        updater = Updater(tg_bot_token)
        dispatcher = updater.dispatcher

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', lambda update, context: start(update, context, redis_db, reply_markup))],

            states={
                QUESTION: [
                    MessageHandler(Filters.regex('^Новый вопрос$'),
                                   lambda update, context: handle_new_question_request(update, context, redis_db, reply_markup, questions_and_answers)),
                    MessageHandler(Filters.regex('^Мой счет$'),
                                   lambda update, context: show_score(update, context, redis_db, reply_markup))
                ],
                ANSWER: [
                    MessageHandler(Filters.text & ~Filters.command & ~Filters.regex('^Новый вопрос$') & ~Filters.regex('^Сдаться$') & ~Filters.regex('^Мой счет$'),
                                   lambda update, context: handle_solution_attempt(update, context, redis_db, reply_markup, questions_and_answers)),
                    MessageHandler(Filters.regex('^Сдаться$'),
                                   lambda update, context: handle_solution_give_up(update, context, redis_db, reply_markup, questions_and_answers)),
                    MessageHandler(Filters.regex('^Новый вопрос$'),
                                   lambda update, context: handle_new_question_request(update, context, redis_db, reply_markup, questions_and_answers)),
                    MessageHandler(Filters.regex('^Мой счет$'),
                                   lambda update, context: show_score(update, context, redis_db, reply_markup))
                ]

            },

            fallbacks=[CommandHandler('cansel', end)]
        )

        dispatcher.add_handler(conv_handler)

        updater.start_polling()
        updater.idle()
    except FileNotFoundError:
        logger.error(f'Файл {questions_file_name} не найден.')
    except Exception as er:
        logger.exception(f'Ошибка {er}')


if __name__ == '__main__':
    main()
