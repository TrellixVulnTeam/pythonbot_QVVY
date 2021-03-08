import json
import os
import re

import requests
from datetime import datetime as dt
import telebot
import zeep
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


def get_attachments_from_posts(post):
    pass


def get_data_from_posts(posts):
    for post in posts:
        text = post["text"]
        attach = post.get("attachments") if post.get("attachments") else []
        if attach:
            get_attachments_from_posts(post)
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


def get_check_digit(num: int) -> int:
    """
    Проверка контрольной цифры в соответствии с форматоом S10
    :param num:
    :return:
    """
    weights = [8, 6, 4, 2, 3, 5, 9, 7]
    control_sum = 0
    for i, digit in enumerate(f"{num:08}"):
        control_sum += weights[i] * int(digit)
    control_sum = 11 - (control_sum % 11)
    if control_sum == 10:
        control_sum = 0
    elif control_sum == 11:
        control_sum = 5
    return control_sum


def chek_barcode(barcode: str):
    """
    Функция проверки трек-номера на корректность
    :param barcode: Идентификатор регистрируемого почтового
            - международный, состоящий из 13 символов (буквенно-цифровой) в формате S10
            - внутрироссийский, состоящий из 14 символов (цифровой)
    :return:
    """
    len_barcode = len(barcode)
    if len_barcode < 13 or len_barcode > 14:
        return False
    if len_barcode == 13:
        if not re.fullmatch("[A-Z]{2}\d{9}[A-Z]{2}", barcode):
            return False
        # Проверка 10-го символа - контрольной цифры по формату S10
        if int(barcode[10]) != get_check_digit(int(barcode[2:10])):
            return False
    else:
        if not re.fullmatch("\d{14}", barcode):
            return False
    return True


def send_message_formatting(location):
    return f"{location.ItemParameters.Barcode.strip()}\n" \
                             f"{location.AddressParameters.OperationAddress.Index.strip()} " \
                             f"{location.AddressParameters.OperationAddress.Description.strip()}\n" \
                             f"{location.OperationParameters.OperDate.strftime('%d.%m.%Y %H:%M:%S %Z')}\n" \
                             f"{location.OperationParameters.OperType.Name} " \
                             f"({location.OperationParameters.OperAttr.Name})"


def get_last_location_russian_post(login: str, password: str, barcode: str):
    """
    Функция возвращает сообщение с данным о почтовом отправлении, псследнее его местонахождение
    :param login: логин в системе API почты Росиии
    :param password: пароль в системе API почты России
    :param barcode:  Трек-номер почтового отправления
    :return:
    """

    # Заменим случайные буквы O на нули
    if len(barcode) == 14:
        barcode = re.sub("O", "0", barcode)
    elif len(barcode) == 13:
        barcode = barcode[0:3] + re.sub("O", "0", barcode[3:10]) + barcode[10:]

    # Проверяем корректность трек-номера
    if not chek_barcode(barcode):
        return "Трек-номер не корректный."

    # Схема WSDL на сайте Почты России. В ней нет указания на необязательность некоторых елементов в ответном сообщеии.
    # wsdl = 'https://tracking.russianpost.ru/tracking-web-static/rtm34_wsdl.xml'
    # Временно используется локальная схема
    wsdl = 'russisnpost\\rtm34_wsdl.xml'

    # Создаём объект по схеме WSDL
    client = zeep.Client(wsdl=wsdl)

    try:
        result = client.service.getOperationHistory({'Barcode': barcode, 'MessageType': 0, 'Language': 'RUS'},
                                                    {'login': login, 'password': password})
        if result:
            last_location = result[len(result) - 1]
            send_message = send_message_formatting(last_location)
        else:
            send_message = f"Отправление с трек-номеро {barcode} не найдено."
    except Exception as ex:
        print(ex)
        print("Что-то пошло нет так. Проверьте правильность трек-номера")
        send_message = f"{ex}\nЧто-то пошло нет так. Проверьте правильность трек-номера."

    return send_message


def telegram_bot(token):
    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=["start"])
    def start_message(message):
        bot.send_message(message.chat.id, "Hello, friend! Write the 'price' to find out of the cost of BTC!")

    @bot.message_handler(content_types=["text"])
    def send_text(message):
        # print(message.text)
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
            # if int(count) > 5:
            #     bot.send_message(message.chat.id, f"Нельзя посмотреть больше 5 последних постов. Даю 5")
            #     count = 5
            post = get_wall_posts_vk(group, count)
            bot.send_message(message.chat.id, f"Группа {post['name_group']} Пост {post['text']}")
        elif message.text.lower()[:6] == "почта:":
            track_number = message.text.upper()[6:].strip()
            if len(track_number) == 0:
                send_message_text = "Хотиле узнать где почтовое отправление?\n Наберите почта:ТРЕКНОМЕР."
            else:
                send_message_text = get_last_location_russian_post(auth_data.russian_post_login,
                                                                   auth_data.russian_pos_password, track_number)
            bot.send_message(message.chat.id, send_message_text)
        else:
            bot.send_message(message.chat.id, "Invalid command. Try again.")

    bot.polling()


def main():
    telegram_bot(auth_data.token_bot)
    # group_name = get_name_from_bot()


if __name__ == '__main__':
    # get_data()
    # telegram_bot(auth_data.token)
    main()
