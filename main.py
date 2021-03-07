import json
import os

import requests
from datetime import datetime as dt
import telebot
import auth_data
# from auth_data import token

# 1626412961:AAEqlkKhInuo3AXtOLAdQaRIeJRhNt0ZiFI

BASE_URL = 'https://api.telegram.org/bot1626412961:AAEqlkKhInuo3AXtOLAdQaRIeJRhNt0ZiFI/'
# r = requests.get(f'{BASE_URL}'


def get_bitcoin_data():
    req = requests.get("https://yobit.net/api/3/ticker/btc_usd")
    response = req.json()
    sell_price = response["btc_usd"]["sell"]
    return f"{dt.now().strftime('%d-%m-%Y %H:%M')}\nSell BTC price: {sell_price}"


def get_data_from_posts(posts):
    for post in posts:
        text = post["text"]
        attach = post["attachments"]
        print(len(attach))
    pass


def get_last_post_vk(group_name):
    url = f"https://api.vk.com/method/wall.get?domain={group_name}&count=1&access_token={auth_data.token_vk}&v=5.130"
    req = requests.get(url)
    # print(req.text)
    src = req.json()
    post = src["response"]["items"]
    print(post)
    post0 = {'name_group': group_name, 'img': 'link to img', 'text': post[0]['text']}
    return post0


def get_wall_posts_vk(group_name, count):
    url = f"https://api.vk.com/method/wall.get?domain={group_name}&count={count}&access_token={auth_data.token_vk}&v=5.130"
    req = requests.get(url)
    src = req.json()
    posts = src["response"]["items"]

    # Проверяем существует ли директория с именем группы
    if os.path.exists(f"{group_name}"):
        print(f"Директория с именем {group_name} уже существует!")
    else:
        os.mkdir(group_name)

    # Сохраним данные в json-файл
    with open(f"{group_name}/{group_name}.json", "w", encoding="utf-8") as file:
        json.dump(src, file, ensure_ascii=False, indent=4)

    # Собираем ID новых постов в список
    fresh_posts_id = []
    for fresh_post_id in posts:
        fresh_posts_id.append(fresh_post_id["id"])

    """ Проверка, если файла не существует, значит это первый парсинг группы ( отправляем все полученные посты).
    Иначе начинаем проверку и отправляем только новые посты."""
    if not os.path.exists(f"{group_name}/exist_post_{group_name}.txt"):
        with open(f"{group_name}/exist_post_{group_name}.txt", "w") as file:
            for item in fresh_posts_id:
                file.write(f"{str(item)}\n")
        get_data_from_posts(posts)
    else:
        print("Файл с ID постов найден, начинаем выбьорку свежих постов")


    post0 = {'name_group': group_name, 'img': 'link to img', 'text': count}
    return post0

def telegram_bot(token):
    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=["start"])
    def start_message(message):
        bot.send_message(message.chat.id, "Hello, friend! Write the 'price' to find out of the cost of BTC!")

    @bot.message_handler(content_types=["text"])
    def send_text(message):
        if message.text.lower() == "price":
            try:
                bot.send_message(
                    message.chat.id,
                    get_bitcoin_data()
                )
            except Exception as ex:
                print(ex)
                bot.send_message(message.chat.id, "Damp...Something was wrong...")
        elif message.text.lower()[:3] == "vk:":
            text = message.text.lower()[3:]
            sep = text.find(":")
            if sep == -1:
                group = text
                count = 1
            else:
                group = text[:sep]
                count = text[sep+1:].strip()
            bot.send_message(message.chat.id, f"Вы хотите узнать о последних {count} постов в {group}")
            if int(count) > 5:
                bot.send_message(message.chat.id, f"Нельзя посмотреть больше 5 последних постов. Даю 5")
                count = 5
            post = get_wall_posts_vk(group, count)
            bot.send_message(message.chat.id, f"Группа {post['name_group']} Пост {post['text']}")
        else:
            bot.send_message(message.chat.id, "Invalid command. Try again.")

    bot.polling()


def main():
    telegram_bot(auth_data.token)
    # group_name = get_name_from_bot()


if __name__ == '__main__':
    # get_data()
    # telegram_bot(auth_data.token)
    main()
