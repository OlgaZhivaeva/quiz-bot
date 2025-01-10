import vk_api as vk
import re
import random
from environs import Env

from vk_api.keyboard import VkKeyboard
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id

from redis_db import r
from quiz_data_parser import logger, questions_and_answers


def start(event, vk_api, keyboard):
    """Send a message to start the quiz."""
    user_id = str(event.user_id)
    vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard(),
        message="Привет! Нажмите 'Новый вопрос' для начала викторины\n"
                " Для отмены нажмите 'Завершить викторину'"
    )
    r.set(f"user:{user_id}:score", "0")


def handle_new_question_request(event, vk_api, keyboard):
    """Handles request for a new question."""
    user_id = str(event.user_id)
    question = random.choice(list(questions_and_answers.keys()))
    r.set(f"user:{user_id}:current_question", question)
    print(f'вопрос:{question}')
    print(f'ответ:{questions_and_answers[question]}')
    vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard(),
        message=question
    )


def handle_solution_attempt(event, vk_api, keyboard):
    """Handles user's attempt to answer a question."""
    user_id = str(event.user_id)
    current_question = r.get(f"user:{user_id}:current_question")
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
        score = int(r.get(f"user:{user_id}:score"))
        r.set(f"user:{user_id}:score", str(score + 1))

    else:
         vk_api.messages.send(
            user_id=event.user_id,
            random_id=get_random_id(),
            keyboard=keyboard.get_keyboard(),
            message='Неправильно… Попробуешь ещё раз?'
        )


def show_score(event, vk_api, keyboard):
    """Shows user's current score."""
    user_id = str(event.user_id)
    score = r.get(f"user:{user_id}:score")

    vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard(),
        message=f'Ваш счет: {score}'
    )


def end(event, vk_api, keyboard):
    """Handles end of quiz"""
    user_id = str(event.user_id)
    score = r.get(f"user:{user_id}:score")
    vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        message=f"Викторина завершена.\nВаш счет {score}."
    )
    r.delete(f"user:{user_id}:score")
    r.delete(f"user:{user_id}:current_question")


def handle_solution_give_up(event, vk_api, keyboard):
    """Handles user giving up on a question."""
    user_id = str(event.user_id)
    current_question = r.get(f"user:{user_id}:current_question")
    correct_answer = questions_and_answers[current_question]
    vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard(),
        message=f'Правильный ответ: {correct_answer}. Для следующего вопроса нажми "Новый вопрос"'
    )


def main():
    env = Env()
    env.read_env()
    vk_group_token = env.str('VK_GROUP_TOKEN')
    vk_session = vk.VkApi(token=vk_group_token)
    vk_api = vk_session.get_api()

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
                    handle_new_question_request(event, vk_api, keyboard)
                elif event.text == 'Сдаться':
                    handle_solution_give_up(event, vk_api, keyboard)
                elif event.text == 'Мой счет':
                    show_score(event, vk_api, keyboard)
                elif event.text == 'Завершить викторину':
                    end(event, vk_api, keyboard)
                else:
                    user_id = str(event.user_id)
                    current_question = r.get(f"user:{user_id}:current_question")
                    if current_question is None:
                        start(event, vk_api, keyboard)
                    else:
                        handle_solution_attempt(event, vk_api, keyboard)
    except Exception as er:
        logger.exception(f'Ошибка {er}')


if __name__ == '__main__':
    main()
