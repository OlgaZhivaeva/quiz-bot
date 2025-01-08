import re
import logging
from pathlib import Path
from environs import Env


env = Env()
env.read_env()
questions_file_name = env.str('QUESTIONS_FILE', '1vs1200.txt')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def load_questions_and_answers(file_path):
    """Downloads and parses questions and answers."""
    try:
        with open(file_path, "r", encoding="KOI8-R") as file:
            file_contents = file.read()

        pattern = re.compile(r'Вопрос \d+:\s*(.*?)\n\nОтвет:\s*(.*?)\n\n', flags=re.DOTALL)
        matches = pattern.findall(file_contents)
        questions_and_answers = {question: answer for question, answer in matches}
        return questions_and_answers
    except FileNotFoundError:
        logger.error(f'Файл {file_path} не найден.')
        return {}
    except Exception as e:
        logger.error(f'Ошибка при загрузке файла: {e}')
        return {}


questions_file_path = Path(__file__).parent / questions_file_name
questions_and_answers = load_questions_and_answers(questions_file_path)


if __name__ == '__main__':
    print(questions_and_answers)
    print(f'Количество вопросов: {len(questions_and_answers)}')






