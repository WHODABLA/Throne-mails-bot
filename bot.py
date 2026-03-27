import telebot
import requests
import random
import string
import threading
import time
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_1 = "@throneex"
CHANNEL_2 = "@dstportal"

bot = telebot.TeleBot(BOT_TOKEN)

BASE = "https://api.mail.tm"
user_data = {}

# ================= FORCE JOIN =================

def is_joined(user_id):
    try:
        ch1 = bot.get_chat_member(CHANNEL_1, user_id)
        ch2 = bot.get_chat_member(CHANNEL_2, user_id)

        return ch1.status in ['member','administrator','creator'] and \
               ch2.status in ['member','administrator','creator']
    except:
        return False

def join_msg(chat_id):
    markup = telebot.types.InlineKeyboardMarkup()

    markup.add(
        telebot.types.InlineKeyboardButton("📢 Join Channel 1", url=f"https://t.me/{CHANNEL_1.replace('@','')}"),
        telebot.types.InlineKeyboardButton("📢 Join Channel 2", url=f"https://t.me/{CHANNEL_2.replace('@','')}")
    )
    markup.add(
        telebot.types.InlineKeyboardButton("✅ Verify", callback_data="verify")
    )

    bot.send_message(
        chat_id,
        "🚫 *Access Denied*\n\nJoin both channels to use this bot.",
        parse_mode="Markdown",
        reply_markup=markup
    )

# ================= EMAIL SYSTEM =================

def create_email():
    domain = requests.get(f"{BASE}/domains").json()['hydra:member'][0]['domain']
    name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    email = f"{name}@{domain}"
    password = "12345678"

    requests.post(f"{BASE}/accounts", json={"address": email,"password": password})

    token = requests.post(f"{BASE}/token", json={"address": email,"password": password}).json()['token']

    return email, token

# ================= AUTO REFRESH =================

def auto_refresh(chat_id, message_id):
    while True:
        time.sleep(5)

        data = user_data.get(chat_id)
        if not data:
            break

        try:
            headers = {"Authorization": f"Bearer {data['token']}"}
            res = requests.get(f"{BASE}/messages", headers=headers).json()
            messages = res.get("hydra:member", [])

            if not messages:
                text = "📭 *Inbox Empty*"
            else:
                text = "📥 *Inbox (Auto Refresh)*\n\n"
                for m in messages[:5]:
                    text += f"📨 `{m['from']['address']}`\n"
                    text += f"📌 `{m['subject']}`\n\n"

            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton("🔄 Refresh", callback_data="inbox"),
                telebot.types.InlineKeyboardButton("🔙 Back", callback_data="menu")
            )

            bot.edit_message_text(
                text,
                chat_id,
                message_id,
                parse_mode="Markdown",
                reply_markup=markup
            )

        except:
            break

# ================= START =================

@bot.message_handler(commands=['start'])
def start(msg):
    if not is_joined(msg.chat.id):
        join_msg(msg.chat.id)
        return

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("📧 Generate Email", callback_data="gen")
    )

    bot.send_message(
        msg.chat.id,
        """🔥 THRONE MAILS

⚡ Fastest Temp Mail Service
📥 Instant Inbox Access
🔐 Secure & Anonymous""",
        parse_mode="Markdown",
        reply_markup=markup
    )

# ================= CALLBACK =================

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    chat_id = call.message.chat.id

    # VERIFY
    if call.data == "verify":
        if is_joined(chat_id):
            bot.answer_callback_query(call.id, "✅ Verified")
            start(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Join both channels")
        return

    # BLOCK IF NOT JOINED
    if not is_joined(chat_id):
        join_msg(chat_id)
        return

    # ================= MENU (FIXED BACK) =================
    if call.data == "menu":
        data = user_data.get(chat_id)

        if not data:
            msg = bot.send_message(chat_id, "⏳ Creating email...")
            try:
                email, token = create_email()
                user_data[chat_id] = {"email": email, "token": token}
            except:
                bot.edit_message_text("❌ Error", chat_id, msg.message_id)
                return

        email = user_data[chat_id]["email"]

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(
            telebot.types.InlineKeyboardButton("📥 Inbox", callback_data="inbox"),
            telebot.types.InlineKeyboardButton("🔄 New Email", callback_data="gen")
        )

        bot.edit_message_text(
            f"📧 *Your Email*\n\n`{email}`",
            chat_id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )

    # ================= GENERATE =================
    elif call.data == "gen":
        msg = bot.send_message(chat_id, "⏳ Creating email...")

        try:
            email, token = create_email()
            user_data[chat_id] = {"email": email, "token": token}

            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton("📥 Inbox", callback_data="inbox"),
                telebot.types.InlineKeyboardButton("🔄 New Email", callback_data="gen")
            )

            bot.edit_message_text(
                f"📧 *Your Email*\n\n`{email}`",
                chat_id,
                msg.message_id,
                parse_mode="Markdown",
                reply_markup=markup
            )

        except:
            bot.edit_message_text("❌ Error generating email", chat_id, msg.message_id)

    # ================= INBOX =================
    elif call.data == "inbox":
        data = user_data.get(chat_id)

        if not data:
            bot.answer_callback_query(call.id, "Generate email first")
            return

        msg = bot.send_message(chat_id, "📥 Loading inbox...")

        try:
            headers = {"Authorization": f"Bearer {data['token']}"}
            res = requests.get(f"{BASE}/messages", headers=headers).json()
            messages = res.get("hydra:member", [])

            if not messages:
                text = "📭 *Inbox Empty*"
            else:
                text = "📥 *Inbox*\n\n"
                for m in messages[:5]:
                    text += f"📨 `{m['from']['address']}`\n"
                    text += f"📌 `{m['subject']}`\n\n"

            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton("🔄 Refresh", callback_data="inbox"),
                telebot.types.InlineKeyboardButton("🔙 Back", callback_data="menu")
            )

            bot.edit_message_text(
                text,
                chat_id,
                msg.message_id,
                parse_mode="Markdown",
                reply_markup=markup
            )

            # AUTO REFRESH THREAD
            threading.Thread(target=auto_refresh, args=(chat_id, msg.message_id)).start()

        except:
            bot.edit_message_text("❌ Inbox error", chat_id, msg.message_id)

# ================= RUN =================

print("🔥 BOT RUNNING...")
bot.infinity_polling()