# Импорт необходимых библиотек и загрузка переменных окружения
from dotenv import load_dotenv
from telebot import TeleBot, types
import json
import os
from datetime import datetime, timedelta


# Загрузка токена бота и данных пользователей из файла
load_dotenv()
TOKEN = os.getenv('SkyengBotToken')
bot = TeleBot(TOKEN)
dictionary = os.getenv('dictionary')
try:
    with open(dictionary, 'r', encoding='utf-8') as f:
        user_data = json.load(f)
        if not isinstance(user_data, dict):
            user_data = {}
        user_data.setdefault("users", [])
        user_data.setdefault("appointments", [])
        user_data.setdefault("reviews", [])
except FileNotFoundError:
    user_data = {}
    user_data.setdefault("users", [])
    user_data.setdefault("appointments", [])
    user_data.setdefault("reviews", [])
    print(f'Файл {dictionary} не найден. Создан новый файл для хранения данных пользователей.')
except Exception as e:
    user_data = {}
    user_data.setdefault("users", [])
    user_data.setdefault("appointments", [])
    user_data.setdefault("reviews", [])
    print(f'Ошибка при загрузке данных пользователей: {e}, сообщите о ней разработчику.')



# Функция для создания клавиатуры с кнопками для выбора даты и времени
def make_keyboard(type, buttons, date=None):

    keyboard = types.InlineKeyboardMarkup()
    for i in range(len(buttons)):
        data = f"{type}_{buttons[i]}"
        if type == 'choose_time':
            data = f"{type}_{date}_{buttons[i]}"
        button = types.InlineKeyboardButton(text=buttons[i], callback_data=data)
        keyboard.add(button)

    return keyboard



# Обработчик для обработки нажатий на кнопки в клавиатуре
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    button_text = call.data.rsplit('_', 1)[1]
    bot.answer_callback_query(call.id, 'Вы нажали кнопку: ' + button_text)
    if button_text == 'Отменить' or button_text == 'Вернуться':
            handle_start(call.message)
            return
    if call.data.startswith('choose_date_'):
        date = button_text
        choose_time(call.message, date)
    elif call.data.startswith('choose_time_'):
        time = button_text
        date = call.data[len('choose_time_'):].rsplit('_', 1)[0]
        add_appointment(date, time, call.message)
    elif call.data.startswith('cancel_appointment_'):
        try:
            date, time = button_text.split(' в ')
            cancel_appointment(date, time, call.message)
        except Exception as e:
            bot.send_message(call.message.chat.id, 'Произошла ошибка при обработке данных для отмены записи. Пожалуйста, попробуйте еще раз.')
            print(f'Ошибка при обработке данных для отмены записи: {button_text}, сообщите о ней разработчику.')
    else:
        if button_text == 'Записаться на прием':
            handle_choose_date(call.message)
        elif button_text == 'Мои записи':
            handle_my_appointments(call.message)
        elif button_text == 'Отменить запись':
            handle_cancel_appointments(call.message)
        elif button_text == 'Отзывы':
            handle_reviews(call.message)
        elif button_text == 'Написать отзыв':
            handle_write_review(call.message)
        elif button_text == 'Изменить имя':
            bot.send_message(call.message.chat.id, 'Пожалуйста, введите новое имя для записи на прием:')
            bot.register_next_step_handler(call.message, register_client)
        else:
            handle_start(call.message)



# Команда /start для приветствия пользователя
@bot.message_handler(commands=['start','menu'])
def handle_start(message):
    # Проверяем, зарегистрирован ли пользователь, и если нет, то регистрируем его
    client_id = str(message.chat.id)
    for user in user_data.get("users", []):
        if user["id"] == client_id:
            break
    else:
        bot.send_message(message.chat.id, 'Пожалуйста, введите свое имя для записи на прием:')
        bot.register_next_step_handler(message, register_client)
        return
    keyboard = make_keyboard('start', ['Записаться на прием', 'Мои записи', 'Отзывы', 'Написать отзыв', 'Изменить имя'])
    bot.send_message(message.chat.id, 'Привет! Что вы хотите сделать?', reply_markup=keyboard)



@bot.message_handler(commands=['change_name'])
def register_client(message):
    try:
        client_name = message.text
    except Exception as e:
        bot.send_message(message.chat.id, 'Произошла ошибка при сохранении данных клиента. Пожалуйста, попробуйте еще раз.')
        print(f'Ошибка при сохранении данных клиента: {e}, сообщите о ней разработчику.')
        return
    for user in user_data.get("users", []):
        if user["id"] == str(message.chat.id):
            keywords = ['cancel', 'отмена', 'отменить']
            if any(keyword in message.text.lower() for keyword in keywords):
                bot.clear_step_handler_by_chat_id(message.chat.id)
                bot.send_message(message.chat.id, 'Действие отменено.')
                handle_start(message)
                return
            user["client_name"] = client_name
            break
    else:
        user_data["users"].append({
            "id": str(message.chat.id),
            "client_name": client_name
        })
    try:
        with open(dictionary, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        bot.send_message(message.chat.id, 'Произошла ошибка при сохранении данных клиента. Пожалуйста, попробуйте еще раз.')
        print(f'Ошибка при сохранении данных клиента: {e}, сообщите о ней разработчику.')
        return
    bot.send_message(message.chat.id, f'Спасибо, {client_name} \nТеперь вы можете записаться на прием.')
    handle_start(message)


# Функция для записи на прием и обработки выбора даты пользователем
@bot.message_handler(commands=['choose_date'])
def handle_choose_date(message):
    global user_data
    text = 'Выберите дату для записи на прием:'
    dates = []
    for i in range(7):
        date = (datetime.now() + timedelta(days=i+3)).strftime('%d-%m-%Y')
        dates.append(date)
    dates.append('Отменить')
    keyboard = make_keyboard('choose_date', dates)
    bot.send_message(message.chat.id, text, reply_markup=keyboard)



# Функция для отображения доступных времен для выбранной даты и обработки выбора времени пользователем
def choose_time(message, date):
    text = f'Вы выбрали дату: {date}. Теперь выберите время для записи на прием:'
    times = ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00']
    appointments = user_data.get('appointments', [])
    for appointment in appointments:
        if appointment["time"] in times and appointment["date"] == date:
            times.remove(appointment["time"])
    if not times:
        bot.send_message(message.chat.id, 'К сожалению, на эту дату нет свободного времени. Пожалуйста, выберите другую дату.')
        handle_choose_date(message)
        return
    times.append('Отменить')
    keyboard = make_keyboard('choose_time', times, date=date)
    bot.send_message(message.chat.id, text, reply_markup=keyboard)



# Функция для добавления записи на прием в данные пользователя и сохранения их в файл
def add_appointment(date, time, message):
    client_id = str(message.chat.id)
    user_data["appointments"].append({
        "date": date,
        "time": time,
        "client_id": client_id
    })
    try:
        with open(dictionary, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        bot.send_message(message.chat.id, 'Произошла ошибка при сохранении данных клиента. Пожалуйста, попробуйте еще раз.')
        print(f'Ошибка при сохранении данных клиента: {e}, сообщите о ней разработчику.')
        return
    keyboard = make_keyboard('start', ['Отменить запись', 'Вернуться'])
    bot.send_message(message.chat.id, f'Запись на прием добавлена: {date} в {time}', reply_markup=keyboard)



# Функция для отображения записей на прием пользователя
@bot.message_handler(commands=['my_appointments'])
def handle_my_appointments(message):
    for user in user_data.get("users", []):
        if user["id"] == str(message.chat.id):
            try:
                client_name = user["client_name"]
            except KeyError:
                client_name = "Неизвестный клиент"
            break
    text = f"Ваши записи на прием под именем {client_name}:\n"
    for appointment in user_data.get("appointments", []):
        if appointment["client_id"] == str(message.chat.id):
            text += f"Дата: {appointment['date']}, Время: {appointment['time']}\n"
    keyboard = make_keyboard('start', ['Записаться на прием','Отменить запись', 'Вернуться'])
    bot.send_message(message.chat.id, text, reply_markup=keyboard)



# Функция для выбора записи на прием для отмены
@bot.message_handler(commands=['cancel_appointments'])
def handle_cancel_appointments(message):
    text = "Выберите запись на прием, которую хотите отменить:"
    appointments = []
    for appointment in user_data.get("appointments", []):
        if appointment["client_id"] == str(message.chat.id):
            appointments.append(f"{appointment['date']} в {appointment['time']}")
    if not appointments:
        bot.send_message(message.chat.id, 'У вас нет записей на прием для отмены.')
        return
    appointments.append('Вернуться')
    keyboard = make_keyboard('cancel_appointment', appointments)
    bot.send_message(message.chat.id, text, reply_markup=keyboard)

# Функция для отмены записи на прием и сохранения изменений в файле
def cancel_appointment(date, time, message):
    global user_data
    for appointment in user_data.get("appointments", []):
        if appointment["client_id"] == str(message.chat.id) and appointment["date"] == date and appointment["time"] == time:
            user_data["appointments"].remove(appointment)
            break
    try:
        with open(dictionary, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        bot.send_message(message.chat.id, 'Произошла ошибка при сохранении данных клиента. Пожалуйста, попробуйте еще раз.')
        print(f'Ошибка при сохранении данных клиента: {e}, сообщите о ней разработчику.')
        return
    keyboard = make_keyboard('start', ['Вернуться'])
    bot.send_message(message.chat.id, f'Запись на прием отменена: {date} в {time}', reply_markup=keyboard)



# Функция для отображения отзывов клиентов
@bot.message_handler(commands=['reviews'])
def handle_reviews(message):
    text = "Отзывы наших клиентов:\n\n"
    for review in user_data.get("reviews", []):
        text += f"{review['client_name']}:\n{review['text']}\n\n"
    keyboard = make_keyboard('start', ['Написать отзыв', 'Вернуться'])
    bot.send_message(message.chat.id, text, reply_markup=keyboard)



# Функция для обработки отзыва и сохранения их в файл
@bot.message_handler(commands=['write_review'])
def handle_write_review(message):
    bot.send_message(message.chat.id, 'Пожалуйста, напишите свой отзыв о нашем сервисе:')
    bot.register_next_step_handler(message, save_review)

# Функция для сохранения отзыва в данные пользователя и сохранения их в файл
def save_review(message):
    keywords = ['cancel', 'отмена', 'отменить']
    if any(keyword in message.text.lower() for keyword in keywords):
        bot.clear_step_handler_by_chat_id(message.chat.id)
        bot.send_message(message.chat.id, 'Действие отменено.')
        handle_start(message)
        return
    try:
        review = message.text
    except Exception as e:
        bot.send_message(message.chat.id, 'Произошла ошибка при сохранении отзыва. Пожалуйста, попробуйте еще раз.')
        print(f'Ошибка при сохранении отзыва: {e}, сообщите о ней разработчику.')
        return
    for user in user_data.get("users", []):
        if user["id"] == str(message.chat.id):
            client_name = user["client_name"]
            break
    user_data["reviews"].append({
        "client_name": client_name,
        "text": review
    })
    with open(dictionary, 'w', encoding='utf-8') as f:
        json.dump(user_data, f, ensure_ascii=False, indent=4)
    keyboard = make_keyboard('start', ['Вернуться'])
    bot.send_message(message.chat.id, 'Спасибо за ваш отзыв!', reply_markup=keyboard)



# Команда /help для получения информации о боте и его возможностях
@bot.message_handler(commands=['help'])
def handle_help(message):
    keyboard = make_keyboard('start', ['Вернуться'])
    bot.send_message(
        message.chat.id,
        'Привет! Это бот для разных задач:\n'
        '/menu - Главное меню\n'
        '/my_appointments - Мои записи\n'
        '/choose_date - Записаться на прием\n'
        '/cancel_appointments - Отменить запись\n'
        '/reviews - Посмотреть отзывы\n'
        '/write_review - Написать отзыв\n'
        '/change_name - Изменить имя\n'
        '/help - Помощь\n'
        'Или просто напишите сообщение, и я постараюсь ответить!\n\n'
        'Бот создан Be1kna для Skyeng.', reply_markup=keyboard)



# Обработчик для всех остальных сообщений, которые не являются командами
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    #Ответы на определенные ключевые слова в сообщении пользователя
    replyText = ''
    if 'привет' in message.text.lower():
        replyText += 'Привет! '
    if 'пока' in message.text.lower():
        replyText += 'Пока! До встречи! '
    if 'как дела' in message.text.lower():
        replyText += 'У меня все отлично! Спасибо, что спросил. '
    if 'как тебя зовут' in message.text.lower():
        replyText += 'Меня зовут Skyeng Bot. А тебя? '
    if 'кто ты' in message.text.lower():
        replyText += 'Я бот, созданный Be1kna. Могу отвечать на сообщения! '
    if 'эхо' in message.text.lower():
        echo_text = message.text[message.text.lower().find('эхо') + len('эхо'):].strip()
        if echo_text == '':
            replyText += 'Пожалуйста, напишите текст после слова "эхо". '
        else:
            replyText += echo_text
    if 'cancel' in message.text.lower() or 'отмена' in message.text.lower() or 'отменить' in message.text.lower():
        replyText += 'У вас нет активных действий для отмены. '
    if replyText == '' and message.chat.type == 'private':
        replyText += 'Извини, я не поняла твое сообщение. '
        keyboard = make_keyboard('start', ['Вернуться'])
        bot.send_message(message.chat.id, replyText, reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, replyText)



# Запуск бота
if __name__ == '__main__':
    print('Bot running...')
    bot.polling(none_stop=True)
