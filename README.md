# Telegram and VK bot for the quiz

Python chatbot for conducting quizzes on Telegram and VKontakte

[tg bot](https://t.me/histori_quiz_bot)

[vk bot](https://vk.com/im?media=&sel=-228903642)

### How to install

Clone the repository
```commandline
git clone https://github.com/OlgaZhivaeva/quiz-bot
```

Create a virtual environment in the project directory and activate it
```commandline
python3 -m venv venv
source venv/bin/activate
```

Python 3 should be already installed. Use `pip` (or `pip3`, if there is a conflict with Python2)
to install dependencies:

```commandline
pip install -r requirements.txt
```

Create a telegram bot 

Create a VK group and get a token from VK API

### Create a Redis database

On the website [Redislabs](https://redis.io/) get the address of the database in the form: redis-13965.f18.us-east-4-9.wc1.cloud.redislabs.com,
its port of the type: 16635 and its password.

### Questions and answers

Prepare a file with questions and answers. Place it in the root of the project.
[sample file](https://github.com/OlgaZhivaeva/quiz-bot/blob/main/1vs1200.txt)

### Environment variables

Create a file `.env` in the project directory:

```commandline
TG_BOT_TOKEN=Your telegram bot token
VK_GROUP_TOKEN=Your VK API token
QUESTIONS_FILE=Your question file
REDIS_HOST=The host for your redis database
REDIS_PORT=The port for your redis database
REDIS_PASSWORD=The password for your redis database
```
### Run the bots

```commandline
python3 tg_bot.py
python3 vk_bot.py
```
Example of tg bot

![Example of tg bot](examination_tg.gif)

Example of vk bot

![Example of vk bot](examination_vk.gif)

### Project Goals

The code is written for educational purposes on online-course for web-developers [dvmn.org](https://dvmn.org/).