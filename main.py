import os
import sqlite3
import telebot
from telebot import types
import math
import logging
import threading
from flask import Flask
import csv
import io
import time
import requests

# Logging စနစ်
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "8753076212:AAHBn4zvIYrrSr3XJTumF6ZgHRSqQqWbT8U"
ADMIN_ID = 8668319365
CHANNEL_USERNAME = "@starmobile63956"  # သင့်ရဲ့ Channel Username
ITEMS_PER_PAGE = 5  # တစ်မျက်နှာလျှင် ပြမည့် နံပါတ်အရေအတွက်

bot = telebot.TeleBot(TOKEN)

# ----------------------------------------------------
# 🌐 Render Free Service မပိတ်သွားစေရန် Flask Web Server & Ping
# ----------------------------------------------------
app = Flask(__name__)
PORT = int(os.environ.get("PORT", 10000))

@app.route('/')
def home():
    return "VIP Phone Numbers Bot is running 24/7 successfully on Render!"

def run_web_server():
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

# Web Server ကို Thread ဖြင့် စတင်ပါမည်
server_thread = threading.Thread(target=run_web_server)
server_thread.daemon = True
server_thread.start()

# ၁၅ မိနစ်တစ်ခါ မအိပ်သွားစေရန် Self-Ping လုပ်ပေးမည့် စနစ်
def keep_alive_ping():
    time.sleep(10) # Server တက်လာသည်အထိ ခေတ္တစောင့်မည်
    while True:
        try:
            # Render App URL သို့မဟုတ် Local Host သို့ လှမ်း Ping ပါမည်
            requests.get(f"http://127.0.0.1:{PORT}")
            logging.info("Keep-alive ping sent successfully.")
        except Exception as e:
            logging.error(f"Keep-alive ping failed: {e}")
        time.sleep(14 * 60) # ၁၄ မိနစ်ခြားတစ်ခါ Ping မည်

ping_thread = threading.Thread(target=keep_alive_ping)
ping_thread.daemon = True
ping_thread.start()

# ----------------------------------------------------
# 🗄️ Database တည်ဆောက်ခြင်း
# ----------------------------------------------------
def init_db():
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS numbers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT,
                operator TEXT,
                price REAL,
                num_type TEXT,
                status TEXT DEFAULT 'AVAILABLE'
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                customer_name TEXT,
                chosen_number TEXT,
                price REAL,
                contact_info TEXT,
                ref_id INTEGER,
                status TEXT DEFAULT 'PENDING',
                date TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT
            )
        ''')
        conn.commit()

init_db()

def register_user(user_id, first_name):
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, first_name) VALUES (?, ?)", (user_id, first_name))
        conn.commit()

# 🔍 ဖုန်းနံပါတ်ကိုကြည့်၍ Operator အလိုအလျောက် ရှာဖွေပေးသည့် Function
def detect_operator(phone):
    p = ''.join(filter(str.isdigit, phone))
    if p.startswith('959'):
        p = '0' + p[2:]
    elif not p.startswith('0'):
        p = '09' + p
        
    if p.startswith(('0975', '0976', '0977', '0978', '0979')):
        return 'ATOM'
    elif p.startswith(('099', '0995', '0996', '0997', '0998', '0999')):
        return 'Ooredoo'
    elif p.startswith(('096', '0966', '0967', '0968', '0969', '0965', '0964')):
        return 'Mytel'
    elif p.startswith(('092', '094', '095', '098', '091')):
        return 'MPT'
    else:
        return 'Other'

# 🔔 Channel Join ပြီးကြောင်း စစ်ဆေးသည့် Function
def check_user_channel(user_id):
    if user_id == ADMIN_ID:
        return True
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except Exception:
        pass
    return False

def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton("✨ နံပါတ်လှများကြည့်မည်"),
        types.KeyboardButton("🍀 Lucky Phone ကြည့်မည်")
    )
    markup.add(
        types.KeyboardButton("📡 Operator အလိုက်ကြည့်မည်"),
        types.KeyboardButton("🔍 နံပါတ်ရှာမည်")
    )
    markup.add(
        types.KeyboardButton("💰 ဈေးနှုန်းအလိုက် ရှာမည်"),
        types.KeyboardButton("📦 ကျွန်ုပ်၏ အော်ဒါများ")
    )
    markup.add(types.KeyboardButton("📞 ဆိုင်နှင့် ဆက်သွယ်ရန်"))
    if user_id == ADMIN_ID:
        markup.add(types.KeyboardButton("👑 Admin Panel"))
    return markup

def not_joined_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📢 Channel သို့သွားရန်", url="https://t.me/starmobile63956"),
        types.InlineKeyboardButton("✅ Join ပြီးပါပြီ (စစ်ဆေးမည်)", callback_data="check_join")
    )
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    register_user(user_id, message.from_user.first_name)
    
    if not check_user_channel(user_id):
        text = (
            "⚠️ *ကျေးဇူးပြု၍ ကျွန်ုပ်တို့၏ Channel ကို အရင် Join ပေးပါ။*\n\n"
            "Bot ကို စတင်အသုံးပြုရန် အောက်ပါ Channel ကို Join ပြီးမှ **'✅ Join ပြီးပါပြီ'** ကို နှိပ်ပေးပါ။"
        )
        bot.send_message(message.chat.id, text, reply_markup=not_joined_markup(), parse_mode="Markdown")
        return

    text = (
        "✨ *Phone Numbers Sales Bot မှ ကြိုဆိုပါတယ်။*\n\n"
        "နံပါတ်လှများနှင့် Lucky Phone များကို အောက်ပါ ခလုတ်များမှတစ်ဆင့် ရွေးချယ် ဝယ်ယူနိုင်ပါပြီခင်ဗျာ။"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_menu(user_id), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def verify_join_callback(call):
    user_id = call.from_user.id
    register_user(user_id, call.from_user.first_name)
    if check_user_channel(user_id):
        bot.answer_callback_query(call.id, "ကျေးဇူးတင်ပါတယ်! Channel Join ပြီးသားဖြစ်တာကို စစ်ဆေးတွေ့ရှိရပါပြီ။")
        text = (
            "✨ *Phone Numbers Sales Bot မှ ကြိုဆိုပါတယ်။*\n\n"
            "နံပါတ်လှများနှင့် Lucky Phone များကို အောက်ပါ ခလုတ်များမှတစ်ဆင့် ရွေးချယ် ဝယ်ယူနိုင်ပါပြီခင်ဗျာ။"
        )
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, text, reply_markup=main_menu(user_id), parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "⚠️ ကျေးဇူးပြု၍ Channel ကို အရင် Join ပေးပါ။", show_alert=True)

def require_channel_join(func):
    def wrapper(message):
        if not check_user_channel(message.from_user.id):
            text = "⚠️ ဤစနစ်ကို အသုံးပြုရန်အတွက် ကျေးဇူးပြု၍ Channel ကို အရင် Join ပေးပါ။"
            bot.send_message(message.chat.id, text, reply_markup=not_joined_markup(), parse_mode="Markdown")
            return
        return func(message)
    return wrapper

# ----------------------------------------------------
# 🛡️ ADMIN COMMANDS (Backup, Restore, Broadcast, Add)
# ----------------------------------------------------

@bot.message_handler(commands=['backup'])
def admin_backup(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        with open('vip_shop.db', 'rb') as f:
            bot.send_document(message.chat.id, f, caption="📦 Database Backup ဖိုင်ရပါပြီ။")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Backup ယူရာတွင် အမှားဖြစ်နေပါသည်: {e}")

@bot.message_handler(content_types=['document'])
def admin_restore(message):
    if message.from_user.id != ADMIN_ID: return
    if message.caption == "/restore" or (message.reply_to_message and message.reply_to_message.document and message.text == "/restore"):
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            with open('vip_shop.db', 'wb') as new_file:
                new_file.write(downloaded_file)
            bot.send_message(message.chat.id, "✅ Database ကို အောင်မြင်စွာ Restore လုပ်ပြီးပါပြီ။")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Restore လုပ်ရာတွင် အမှားဖြစ်နေပါသည်: {e}")

@bot.message_handler(commands=['broadcast'])
def admin_broadcast(message):
    if message.from_user.id != ADMIN_ID: return
    text_to_send = message.text.replace("/broadcast", "").strip()
    if not text_to_send:
        bot.send_message(message.chat.id, "❌ ပေးပို့လိုသော စာသားကို ထည့်ပါ။\nဥပမာ: `/broadcast မင်္ဂလာပါ`", parse_mode="Markdown")
        return
        
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        
    bot.send_message(message.chat.id, "⏳ Broadcast စတင်နေပါပြီ...")
    success = 0
    for u in users:
        try:
            bot.send_message(u[0], text_to_send)
            success += 1
        except Exception:
            pass
    bot.send_message(message.chat.id, f"✅ စုစုပေါင်း လူ {success} ဦးထံသို့ Message ပေးပို့ပြီးပါပြီ။")

@bot.message_handler(commands=['addnum'])
def admin_add_number(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        data = message.text.replace("/addnum", "").strip()
        parts = data.split(',')
        if len(parts) != 3:
            bot.send_message(message.chat.id, "❌ ပုံစံမှားနေပါသည်။ Comma (,) ခံ၍ရေးပါ။\nFormat: `/addnum ဖုန်းနံပါတ်, ဈေးနှုန်း, အမျိုးအစား`\nဥပမာ: `/addnum 09 777 888 999, 150000, PRO`", parse_mode="Markdown")
            return
            
        raw_phone = parts[0]
        price = float(parts[1].strip())
        num_type = parts[2].strip().upper()
        
        # Space အပိုများကို Auto ဖြုတ်ပေးမည်
        phone = ''.join(filter(str.isdigit, raw_phone))
        op = detect_operator(phone)
        
        with sqlite3.connect('vip_shop.db') as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO numbers (phone_number, operator, price, num_type) VALUES (?, ?, ?, ?)", (phone, op, price, num_type))
            conn.commit()
            
        bot.send_message(message.chat.id, f"✅ နံပါတ်အသစ် ထည့်သွင်းပြီးပါပြီ။\n\n📱 <b>Phone:</b> {phone}\n📡 <b>Operator:</b> {op}\n💰 <b>Price:</b> {price:,.0f}\n✨ <b>Type:</b> {num_type}", parse_mode="HTML")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ အမှားဖြစ်နေပါသည်: {e}")

# ----------------------------------------------------
# 🛍️ USER SHOPPING LOGIC
# ----------------------------------------------------

# ✨ နံပါတ်လှများ ပြသခြင်း (Pagination ဖြင့်)
@bot.message_handler(func=lambda m: m.text == "✨ နံပါတ်လှများကြည့်မည်")
@require_channel_join
def show_pro_numbers(message):
    send_paginated_numbers(message.chat.id, "PRO", 0, is_edit=False, message_id=None)

# 🍀 Lucky Phone ပြသခြင်း (Pagination ဖြင့်)
@bot.message_handler(func=lambda m: m.text == "🍀 Lucky Phone ကြည့်မည်")
@require_channel_join
def show_lucky_numbers(message):
    send_paginated_numbers(message.chat.id, "LUCKY", 0, is_edit=False, message_id=None)

def send_paginated_numbers(chat_id, n_type, page, is_edit=False, message_id=None):
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM numbers WHERE num_type=? AND status='AVAILABLE'", (n_type,))
        total_items = cursor.fetchone()[0]

    if total_items == 0:
        text = "📭 လောလောဆယ် ဤစာရင်းတွင် နံပါတ်များ မရှိသေးပါ။"
        if is_edit:
            bot.edit_message_text(text, chat_id, message_id)
        else:
            bot.send_message(chat_id, text)
        return

    total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
    offset = page * ITEMS_PER_PAGE

    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, phone_number, operator, price FROM numbers WHERE num_type=? AND status='AVAILABLE' LIMIT ? OFFSET ?", (n_type, ITEMS_PER_PAGE, offset))
        rows = cursor.fetchall()

    title = "✨ ရောင်းရန်ရှိသော နံပါတ်လှများ -" if n_type == "PRO" else "🍀 ရောင်းရန်ရှိသော Lucky Phone များ -"
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for row in rows:
        n_id, phone, op, price = row
        btn_text = f"📱 {phone} ({op}) - {price:,.0f} ကျပ်"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"buy_{n_id}"))

    # Pagination ခလုတ်များ
    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ ရှေ့သို့", callback_data=f"page_{n_type}_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton("နောက်သို့ ➡️", callback_data=f"page_{n_type}_{page+1}"))
    
    if nav_buttons:
        markup.row(*nav_buttons)

    if is_edit:
        bot.edit_message_text(f"{title} (စာမျက်နှာ {page+1}/{total_pages})", chat_id, message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, f"{title} (စာမျက်နှာ {page+1}/{total_pages})", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("page_"))
def handle_pagination(call):
    if not check_user_channel(call.from_user.id):
        bot.answer_callback_query(call.id, "⚠️ ကျေးဇူးပြု၍ Channel ကို အရင် Join ပေးပါ။", show_alert=True)
        return

    parts = call.data.split("_")
    n_type = parts[1]
    page = int(parts[2])
    send_paginated_numbers(call.message.chat.id, n_type, page, is_edit=True, message_id=call.message.message_id)

# 📡 Operator အလိုက် ခွဲခြားပြခြင်း
@bot.message_handler(func=lambda m: m.text == "📡 Operator အလိုက်ကြည့်မည်")
@require_channel_join
def show_operators(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("MPT", callback_data="op_MPT"),
        types.InlineKeyboardButton("ATOM", callback_data="op_ATOM"),
        types.InlineKeyboardButton("Ooredoo", callback_data="op_Ooredoo"),
        types.InlineKeyboardButton("Mytel", callback_data="op_Mytel")
    )
    bot.send_message(message.chat.id, "ကြည့်ရှုလိုသော အော်ပရေတာကို ရွေးချယ်ပါ -", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("op_"))
def filter_by_operator(call):
    if not check_user_channel(call.from_user.id):
        bot.answer_callback_query(call.id, "⚠️ ကျေးဇူးပြု၍ Channel ကို အရင် Join ပေးပါ။", show_alert=True)
        return

    op_name = call.data.split("_")[1]
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, phone_number, price, num_type FROM numbers WHERE operator=? AND status='AVAILABLE'", (op_name,))
        rows = cursor.fetchall()

    if not rows:
        bot.answer_callback_query(call.id, f"{op_name} နံပါတ်များ လောလောဆယ် မရှိသေးပါ။")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for row in rows:
        n_id, phone, price, n_type = row
        tag = "✨ နံပါတ်လှ" if n_type == "PRO" else "🍀 Lucky"
        btn_text = f"[{tag}] {phone} - {price:,.0f} ကျပ်"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"buy_{n_id}"))
            
    bot.edit_message_text(f"📡 *{op_name}* ရရှိနိုင်သော နံပါတ်များ -", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

# 💰 ဈေးနှုန်းအလိုက် ရှာဖွေခြင်း (Price Filter)
@bot.message_handler(func=lambda m: m.text == "💰 ဈေးနှုန်းအလိုက် ရှာမည်")
@require_channel_join
def price_filter_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔹 ၁ သိန်းအောက်", callback_data="pr_0_100000"),
        types.InlineKeyboardButton("🔹 ၁ သိန်း - ၅ သိန်း", callback_data="pr_100000_500000"),
        types.InlineKeyboardButton("🔹 ၅ သိန်း - ၁၀ သိန်း", callback_data="pr_500000_1000000"),
        types.InlineKeyboardButton("🔹 ၁၀ သိန်းအထက်", callback_data="pr_1000000_999999999")
    )
    bot.send_message(message.chat.id, "💰 ကြည့်ရှုလိုသော ဈေးနှုန်းအကွာအဝေးကို ရွေးချယ်ပါ -", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pr_"))
def filter_by_price(call):
    if not check_user_channel(call.from_user.id):
        bot.answer_callback_query(call.id, "⚠️ ကျေးဇူးပြု၍ Channel ကို အရင် Join ပေးပါ။", show_alert=True)
        return

    parts = call.data.split("_")
    min_p = float(parts[1])
    max_p = float(parts[2])

    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, phone_number, operator, price, num_type FROM numbers WHERE price BETWEEN ? AND ? AND status='AVAILABLE'", (min_p, max_p))
        rows = cursor.fetchall()

    if not rows:
        bot.answer_callback_query(call.id, "ဤဈေးနှုန်းအတွင်း ရရှိနိုင်သော နံပါတ်များ မရှိသေးပါ။", show_alert=True)
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for row in rows:
        n_id, phone, op, price, n_type = row
        tag = "✨ နံပါတ်လှ" if n_type == "PRO" else "🍀 Lucky"
        btn_text = f"[{tag}] {phone} ({op}) - {price:,.0f} ကျပ်"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"buy_{n_id}"))

    bot.edit_message_text("💰 ရွေးချယ်ထားသော ဈေးနှုန်းအတွင်းရှိ နံပါတ်များ -", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

# 🔍 နံပါတ်ရှာဖွေခြင်း
@bot.message_handler(func=lambda m: m.text == "🔍 နံပါတ်ရှာမည်")
@require_channel_join
def search_number(message):
    msg = bot.send_message(message.chat.id, "🔍 သင်ရှာဖွေလိုသော ဂဏန်းကို ရိုက်ထည့်ပါ\n*(ဥပမာ - 777 သို့မဟုတ် 9999)*", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_search)

def process_search(message):
    if not check_user_channel(message.from_user.id):
        return

    keyword = message.text.strip()
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, phone_number, operator, price, num_type FROM numbers WHERE phone_number LIKE ? AND status='AVAILABLE'", (f'%{keyword}%',))
        rows = cursor.fetchall()

    if not rows:
        bot.send_message(message.chat.id, f"❌ `{keyword}` ပါဝင်သော နံပါတ်များ ရှာမတွေ့ပါ။", parse_mode="Markdown")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for row in rows:
        n_id, phone, op, price, n_type = row
        tag = "✨ နံပါတ်လှ" if n_type == "PRO" else "🍀 Lucky"
        btn_text = f"[{tag}] {phone} ({op}) - {price:,.0f} ကျပ်"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"buy_{n_id}"))
    
    bot.send_message(message.chat.id, f"🔍 `{keyword}` ပါဝင်သော နံပါတ်များ -", reply_markup=markup, parse_mode="Markdown")

# 📦 ကျွန်ုပ်၏ အော်ဒါများ (My Orders & Cancel)
@bot.message_handler(func=lambda m: m.text == "📦 ကျွန်ုပ်၏ အော်ဒါများ" or m.text == "/myorders")
@require_channel_join
def show_my_orders(message):
    user_id = message.from_user.id
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, chosen_number, price, contact_info, status, date FROM orders WHERE user_id=? AND status='PENDING'", (user_id,))
        rows = cursor.fetchall()

    if not rows:
        bot.send_message(message.chat.id, "📭 လောလောဆယ် ဆောင်ရွက်ဆဲ (Pending) အော်ဒါမှတ်တမ်း မရှိပါ။")
        return

    for row in rows:
        o_id, phone, price, contact_info, status, date = row
        order_code = f"#ORD-{o_id:03d}"
        
        text = (
            f"📦 **အော်ဒါနံပါတ်:** `{order_code}`\n"
            f"📱 **မှာယူသည့်နံပါတ်:** `{phone}`\n"
            f"💰 **ကျသင့်ငွေ:** `{price:,.0f}` ကျပ်\n"
            f"📍 **လိပ်စာ:** {contact_info}\n"
         
