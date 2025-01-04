import re

with open("1vs1200.txt", "r", encoding="KOI8-R") as file:
    file_contents = file.read()

pattern = re.compile(r'Вопрос \d+:\s*(.*?)\n\nОтвет:\s*(.*?)\n\n', flags=re.DOTALL)
matches = pattern.findall(file_contents)
questions_and_answers = {question: answer for question, answer in matches}

# for key, value in questions_and_answers.items():
#     print('вопрос:')
#     print(key)
#     print('ответ:')
#     print(value)
#     print('----------------------------------------------------------------------')




