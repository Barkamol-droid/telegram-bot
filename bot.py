# -*- coding: utf-8 -*-
import os
import json
import time
from datetime import datetime

import telebot
from telebot import types

TOKEN = "8514774065:AAG4HXOqJfgMMXmTmXtQsUnFGSWwGBkB50A"
ADMIN_IDS = [356421765, 8007501282]
CHANNELS = ["@jahonkinotop", "@azure_jewelry"]

DB_FILE = "movies.json"
USERS_FILE = "users.json"

bot = telebot.TeleBot(TOKEN, threaded=False)

user_states = {}


def ensure_file(filename, default_data):
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            json.dump(default_data, f)


def load_json(filename, default_data):
    ensure_file(filename, default_data)
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except:
        return default_data


def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f)


def is_admin(user_id):
    return user_id in ADMIN_IDS


def add_user(user_id):
    users = load_json(USERS_FILE, [])
    if user_id not in users:
        users.append(user_id)
        save_json(USERS_FILE, users)


def get_movies():
    return load_json(DB_FILE, [])


def save_movies(movies):
    save_json(DB_FILE, movies)


def check_subscribed(user_id):
    for channel in CHANNELS:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True


def sub_keyboard():
    kb = types.InlineKeyboardMarkup()
    for ch in CHANNELS:
        kb.add(types.InlineKeyboardButton(ch, url="https://t.me/" + ch.replace("@", "")))
    kb.add(types.InlineKeyboardButton("Tekshirish", callback_data="check_sub"))
    return kb


def main_menu(user_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Kino qidirish", "Kategoriyalar")
    kb.row("Adminga yozish")
    if is_admin(user_id):
        kb.row("Kino qoshish", "Kino ochirish")
        kb.row("Reklama yuborish", "Statistika")
    return kb


def cancel_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Bekor qilish")
    return kb


def get_categories():
    movies = get_movies()
    cats = []
    for movie in movies:
        cat = movie.get("category", "Boshqa")
        if cat not in cats:
            cats.append(cat)
    return cats


def category_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    cats = get_categories()
    if not cats:
        kb.add(types.InlineKeyboardButton("Kategoriya yoq", callback_data="none"))
        return kb

    buttons = []
    for cat in cats:
        buttons.append(types.InlineKeyboardButton(cat, callback_data="cat_" + cat))

    for i in range(0, len(buttons), 2):
        kb.row(*buttons[i:i + 2])

    return kb


def find_movie_by_code(code):
    movies = get_movies()
    for movie in movies:
        if str(movie.get("code")) == str(code):
            return movie
    return None


def search_movies(query):
    query = query.lower().strip()
    movies = get_movies()
    results = []
    for movie in movies:
        title = str(movie.get("title", "")).lower()
        code = str(movie.get("code", "")).lower()
        category = str(movie.get("category", "")).lower()

        if query in title or query == code or query in category:
            results.append(movie)
    return results


def send_movie(chat_id, movie):
    title = movie.get("title", "Nomsiz kino")
    code = movie.get("code", "0000")
    category = movie.get("category", "Boshqa")
    description = movie.get("description", "Tavsif yoq")
    video = movie.get("video", "")

    text = (
        "Kino: " + title + "\n"
        "Kod: " + str(code) + "\n"
        "Kategoriya: " + category + "\n"
        "Tavsif: " + description
    )

    if video:
        try:
            bot.send_video(chat_id, video, caption=text)
            return
        except:
            pass

    bot.send_message(chat_id, text)


@bot.message_handler(commands=["start"])
def start_handler(message):
    user_id = message.from_user.id
    add_user(user_id)

    if not check_subscribed(user_id):
        bot.send_message(
            message.chat.id,
            "Botdan foydalanish uchun oldin kanallarga obuna boling.",
            reply_markup=sub_keyboard()
        )
        return

    bot.send_message(
        message.chat.id,
        "Xush kelibsiz. Kerakli bolimni tanlang.",
        reply_markup=main_menu(user_id)
    )


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id

    if call.data == "check_sub":
        if check_subscribed(user_id):
            bot.answer_callback_query(call.id, "Tasdiqlandi")
            bot.send_message(
                call.message.chat.id,
                "Obuna tekshirildi. Endi foydalanishingiz mumkin.",
                reply_markup=main_menu(user_id)
            )
        else:
            bot.answer_callback_query(call.id, "Hali obuna bolmagansiz", show_alert=True)

    elif call.data == "none":
        bot.answer_callback_query(call.id, "Kategoriya yoq")

    elif call.data.startswith("cat_"):
        cat = call.data[4:]
        movies = get_movies()
        found = False
        for movie in movies:
            if movie.get("category", "") == cat:
                send_movie(call.message.chat.id, movie)
                found = True
        if not found:
            bot.send_message(call.message.chat.id, "Bu kategoriyada kino topilmadi")


@bot.message_handler(func=lambda m: m.text == "Kino qidirish")
def search_start(message):
    user_states[message.from_user.id] = {"action": "search"}
    bot.send_message(
        message.chat.id,
        "Kino nomini yoki kodini yuboring.",
        reply_markup=cancel_menu()
    )


@bot.message_handler(func=lambda m: m.text == "Kategoriyalar")
def categories_handler(message):
    bot.send_message(
        message.chat.id,
        "Kategoriyalardan birini tanlang.",
        reply_markup=category_keyboard()
    )


@bot.message_handler(func=lambda m: m.text == "Adminga yozish")
def support_start(message):
    user_states[message.from_user.id] = {"action": "support"}
    bot.send_message(
        message.chat.id,
        "Xabaringizni yuboring.",
        reply_markup=cancel_menu()
    )


@bot.message_handler(func=lambda m: m.text == "Statistika" and is_admin(m.from_user.id))
def stats_handler(message):
    users = load_json(USERS_FILE, [])
    movies = get_movies()
    text = (
        "Foydalanuvchilar soni: " + str(len(users)) + "\n"
        "Kinolar soni: " + str(len(movies))
    )
    bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda m: m.text == "Kino qoshish" and is_admin(m.from_user.id))
def add_movie_start(message):
    user_states[message.from_user.id] = {"action": "add_movie", "step": 1}
    bot.send_message(
        message.chat.id,
        "1-qadam. Kino kodini yuboring.",
        reply_markup=cancel_menu()
    )


@bot.message_handler(func=lambda m: m.text == "Kino ochirish" and is_admin(m.from_user.id))
def delete_movie_start(message):
    user_states[message.from_user.id] = {"action": "delete_movie"}
    bot.send_message(
        message.chat.id,
        "Ochirmoqchi bolgan kino kodini yuboring.",
        reply_markup=cancel_menu()
    )


@bot.message_handler(func=lambda m: m.text == "Reklama yuborish" and is_admin(m.from_user.id))
def broadcast_start(message):
    user_states[message.from_user.id] = {"action": "broadcast", "step": 1}
    bot.send_message(
        message.chat.id,
        "1-qadam. Reklama matnini yuboring.",
        reply_markup=cancel_menu()
    )


@bot.message_handler(func=lambda m: m.text == "Bekor qilish")
def cancel_handler(message):
    user_id = message.from_user.id
    if user_id in user_states:
        del user_states[user_id]
    bot.send_message(
        message.chat.id,
        "Amal bekor qilindi.",
        reply_markup=main_menu(user_id)
    )


@bot.message_handler(content_types=["text", "video"])
def all_handler(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if not check_subscribed(user_id):
        bot.send_message(
            chat_id,
            "Oldin kanallarga obuna boling.",
            reply_markup=sub_keyboard()
        )
        return

    if user_id not in user_states:
        return

    state = user_states[user_id]
    action = state.get("action")

    if action == "search":
        query = message.text.strip()
        results = search_movies(query)
        del user_states[user_id]

        if not results:
            bot.send_message(chat_id, "Hech narsa topilmadi.", reply_markup=main_menu(user_id))
            return

        bot.send_message(chat_id, "Topilgan kinolar:", reply_markup=main_menu(user_id))
        for movie in results[:10]:
            send_movie(chat_id, movie)
        return

    if action == "support":
        text = message.text if message.content_type == "text" else "Video yuborildi"
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(
                    admin_id,
                    "Yangi murojaat\nUser ID: " + str(user_id) + "\nXabar: " + text
                )
            except:
                pass

        del user_states[user_id]
        bot.send_message(chat_id, "Xabaringiz adminga yuborildi.", reply_markup=main_menu(user_id))
        return

    if action == "add_movie" and is_admin(user_id):
        step = state.get("step", 1)

        if step == 1:
            code = message.text.strip()
            if find_movie_by_code(code):
                bot.send_message(chat_id, "Bu kod oldin ishlatilgan. Boshqa kod yuboring.")
                return
            state["code"] = code
            state["step"] = 2
            bot.send_message(chat_id, "2-qadam. Kino nomini yuboring.")
            return

        if step == 2:
            state["title"] = message.text.strip()
            state["step"] = 3
            bot.send_message(chat_id, "3-qadam. Kategoriya nomini yuboring.")
            return

        if step == 3:
            state["category"] = message.text.strip()
            state["step"] = 4
            bot.send_message(chat_id, "4-qadam. Tavsif yuboring.")
            return

        if step == 4:
            state["description"] = message.text.strip()
            state["step"] = 5
            bot.send_message(chat_id, "5-qadam. Video yuboring yoki skip deb yozing.")
            return

        if step == 5:
            video_id = ""
            if message.content_type == "video":
                video_id = message.video.file_id
            elif message.content_type == "text" and message.text.lower() == "skip":
                video_id = ""
            else:
                bot.send_message(chat_id, "Video yuboring yoki skip deb yozing.")
                return

            movies = get_movies()
            movies.append({
                "code": state["code"],
                "title": state["title"],
                "category": state["category"],
                "description": state["description"],
                "video": video_id,
                "created_at": str(datetime.now())
            })
            save_movies(movies)

            del user_states[user_id]
            bot.send_message(chat_id, "Kino saqlandi.", reply_markup=main_menu(user_id))
            return

    if action == "delete_movie" and is_admin(user_id):
        code = message.text.strip()
        movies = get_movies()
        new_movies = []

        for movie in movies:
            if str(movie.get("code")) != code:
                new_movies.append(movie)

        if len(new_movies) == len(movies):
            bot.send_message(chat_id, "Bunday kod topilmadi.")
            return

        save_movies(new_movies)
        del user_states[user_id]
        bot.send_message(chat_id, "Kino ochirildi.", reply_markup=main_menu(user_id))
        return

    if action == "broadcast" and is_admin(user_id):
        step = state.get("step", 1)

        if step == 1:
            state["text"] = message.text
            state["step"] = 2
            bot.send_message(chat_id, "2-qadam. Tugma matnini yuboring.")
            return

        if step == 2:
            state["button_text"] = message.text
            state["step"] = 3
            bot.send_message(chat_id, "3-qadam. Tugma linkini yuboring.")
            return

        if step == 3:
            state["button_url"] = message.text.strip()

            users = load_json(USERS_FILE, [])
            sent = 0
            failed = 0

            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton(state["button_text"], url=state["button_url"]))

            for uid in users:
                try:
                    bot.send_message(uid, state["text"], reply_markup=kb)
                    sent += 1
                    time.sleep(0.05)
                except:
                    failed += 1

            del user_states[user_id]
            bot.send_message(
                chat_id,
                "Reklama yuborildi.\nYuborildi: " + str(sent) + "\nXato: " + str(failed),
                reply_markup=main_menu(user_id)
            )
            return


print("Bot ishga tushdi")

while True:
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print("Xatolik:", e)
        time.sleep(3)