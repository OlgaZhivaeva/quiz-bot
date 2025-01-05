import vk_api as vk
import re
import random
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id
from environs import Env
from vk_api.longpoll import VkLongPoll, VkEventType

from tg_bot import logger
from questions_and_answers import questions_and_answers


def start(event, vk_api, keyboard):
    """Send a message to start the quiz."""
    vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard(),
        message="Привет! Нажмите 'Новый вопрос' для начала викторины\n"
                " Для отмены нажмите 'Завершить викторину'"
    )


def handle_new_question_request(user_data, event, vk_api, keyboard):
    """Handles request for a new question."""
    question = random.choice(list(questions_and_answers.keys()))
    user_data[event.user_id]['current_question'] = question
    print(f'вопрос:{question}')
    print(f'ответ:{questions_and_answers[question]}')
    vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard(),
        message=question
    )


def handle_solution_attempt(user_data, event, vk_api, keyboard):
    """Handles user's attempt to answer a question."""
    current_question = user_data[event.user_id]['current_question']
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
        user_data[event.user_id]['score'] += 1

    else:
         vk_api.messages.send(
            user_id=event.user_id,
            random_id=get_random_id(),
            keyboard=keyboard.get_keyboard(),
            message='Неправильно… Попробуешь ещё раз?'
        )


def show_score(user_data, event, vk_api, keyboard):
    """Shows user's current score."""
    score = user_data[event.user_id].get('score', 0)

    vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard(),
        message=f'Ваш счет: {score}'
    )


def end(user_data, event, vk_api, keyboard):
    """Handles end of quiz"""
    score = user_data[event.user_id].get('score', 0)
    vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        message=f"Викторина завершена.\nВаш счет {score}."
    )
    user_data.clear()


def handle_solution_give_up(user_data, event, vk_api, keyboard):
    """Handles user giving up on a question."""
    current_question = user_data[event.user_id].get("current_question")
    correct_answer = questions_and_answers[current_question]
    vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard(),
        message=f'Правильный ответ: {correct_answer}. Для следующего вопроса нажми "Новый вопрос"'
    )


def main():
    user_data = {}
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

    longpoll = VkLongPoll(vk_session)
    logger.info('vk-бот запущен')
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            user_id = event.user_id
            if user_id not in user_data:
                user_data[user_id] = {'current_question': None, 'score': 0}
                start(event, vk_api, keyboard)
            elif event.text == 'Новый вопрос':
                handle_new_question_request(user_data, event, vk_api, keyboard)
            elif event.text == 'Сдаться':
                handle_solution_give_up(user_data, event, vk_api, keyboard)
            elif event.text == 'Мой счет':
                show_score(user_data, event, vk_api, keyboard)
            elif event.text == 'Завершить викторину':
                end(user_data, event, vk_api, keyboard)
            else:
                handle_solution_attempt(user_data, event, vk_api, keyboard)


if __name__ == '__main__':
    main()
