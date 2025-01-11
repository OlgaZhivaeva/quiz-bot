import logging
import vk_api as vk
import random
import re
import redis

from environs import Env
from vk_api.keyboard import VkKeyboard
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id

from quiz_data_parser import get_questions_and_answers


logger = logging.getLogger(__name__)


def start(redis_db, event, vk_api, keyboard):
    """Send a message to start the quiz."""
    user_id = event.user_id
    vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard(),
        message="Привет! Нажмите 'Новый вопрос' для начала викторины\n"
                " Для отмены нажмите 'Завершить викторину'"
    )
    redis_db.set(f"user:{user_id}:score", "0")


def handle_new_question_request(redis_db, questions_and_answers, event, vk_api, keyboard):
    """Handles request for a new question."""
    user_id = event.user_id
    question = random.choice(list(questions_and_answers.keys()))
    redis_db.set(f"user:{user_id}:current_question", question)
    vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard(),
        message=question
    )


def handle_solution_attempt(redis_db, questions_and_answers, event, vk_api, keyboard):
    """Handles user's attempt to answer a question."""
    user_id = event.user_id
    current_question = redis_db.get(f"user:{user_id}:current_question")
    correct_answer = questions_and_answers[current_question]
    smart_correct_answer = re.search(r'^[^(^.]+', correct_answer).group().lower().strip().strip("'\"")
    user_answer = re.search(r'^[^.]+', event.text).group().lower().strip()

    if user_answer == smart_correct_answer:
        vk_api.messages.send(
            user_id=event.user_id,
            random_id=get_random_id(),
            keyboard=keyboard.get_keyboard(),
            message='Правильно! Поздравляю! Для следующего вопроса нажми "Новый вопрос"'
        )
        score = int(redis_db.get(f"user:{user_id}:score"))
        redis_db.set(f"user:{user_id}:score", str(score + 1))

    else:
         vk_api.messages.send(
            user_id=event.user_id,
            random_id=get_random_id(),
            keyboard=keyboard.get_keyboard(),
            message='Неправильно… Попробуешь ещё раз?'
        )


def show_score(redis_db, event, vk_api, keyboard):
    """Shows user's current score."""
    user_id = event.user_id
    score = redis_db.get(f"user:{user_id}:score")

    vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard(),
        message=f'Ваш счет: {score}'
    )


def end(redis_db, event, vk_api):
    """Handles end of quiz"""
    user_id = event.user_id
    score = redis_db.get(f"user:{user_id}:score")
    vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        message=f"Викторина завершена.\nВаш счет {score}."
    )
    redis_db.delete(f"user:{user_id}:score")
    redis_db.delete(f"user:{user_id}:current_question")


def handle_solution_give_up(redis_db, questions_and_answers, event, vk_api, keyboard):
    """Handles user giving up on a question."""
    user_id = event.user_id
    current_question = redis_db.get(f"user:{user_id}:current_question")
    correct_answer = questions_and_answers[current_question]
    vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard(),
        message=f'Правильный ответ: {correct_answer}. Для следующего вопроса нажми "Новый вопрос"'
    )


def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
    )
    logger.setLevel(logging.DEBUG)

    env = Env()
    env.read_env()
    vk_group_token = env.str('VK_GROUP_TOKEN')
    vk_session = vk.VkApi(token=vk_group_token)
    vk_api = vk_session.get_api()
    redis_host = env.str('REDIS_HOST')
    redis_port = env.str('REDIS_PORT')
    redis_password = env.str('REDIS_PASSWORD')
    redis_db = redis.StrictRedis(
        host=redis_host,
        port=redis_port,
        decode_responses=True,
        charset="utf-8",
        password=redis_password,
    )

    questions_and_answers = get_questions_and_answers()

    keyboard = VkKeyboard(one_time=True)

    keyboard.add_button('Новый вопрос', color="primary")
    keyboard.add_button('Сдаться', color="negative")

    keyboard.add_line()  # Переход на вторую строку
    keyboard.add_button('Мой счет', color="default")
    keyboard.add_line()  # Переход на вторую строку
    keyboard.add_button('Завершить викторину', color="positive")

    try:
        longpoll = VkLongPoll(vk_session)
        logger.info('vk-бот запущен')
        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                if event.text == 'Новый вопрос':
                    handle_new_question_request(redis_db, questions_and_answers, event, vk_api, keyboard)
                elif event.text == 'Сдаться':
                    handle_solution_give_up(redis_db, questions_and_answers, event, vk_api, keyboard)
                elif event.text == 'Мой счет':
                    show_score(redis_db, event, vk_api, keyboard)
                elif event.text == 'Завершить викторину':
                    end(redis_db, event, vk_api)
                else:
                    user_id = event.user_id
                    current_question = redis_db.get(f"user:{user_id}:current_question")
                    if current_question:
                        handle_solution_attempt(redis_db, questions_and_answers, event, vk_api, keyboard)
                        continue
                    start(redis_db, event, vk_api, keyboard)

    except Exception as er:
        logger.exception(f'Ошибка {er}')


if __name__ == '__main__':
    main()
