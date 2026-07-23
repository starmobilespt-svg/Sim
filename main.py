import os
import sqlite3
import telebot
from telebot import types
import math
import logging
import threading
from flask import Flask

# Logging စနစ်
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "8753076212:AAHBn4zvIYrrSr3XJTumF6ZgHRSqQqWbT8U"
ADMIN_ID = 8668319365
CHANNEL_USERNAME = "@starmobile63956"

ITEMS_PER_PAGE = 5

bot = telebot.TeleBot(TOKEN)

# ----------------------------------------------------
# Render မပိတ်သွားစေရန် Flask Web Server
# ----------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "VIP Shop Bot is running 24/7 on Render!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web_server, daemon=True).start()

# ----------------------------------------------------
# Database စနစ်
# ----------------------------------------------------
def init_db():
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
        
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
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                title TEXT,
                price REAL,
                details TEXT,
                status TEXT DEFAULT 'AVAILABLE'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                customer_name TEXT,
                item_type TEXT,
                chosen_item TEXT,
                price REAL,
                contact_info TEXT,
                ref_id INTEGER,
                status TEXT DEFAULT 'PENDING',
                date TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('deli_fee', '4000')")
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('kpay_no', '09795096484 (Si Thu Aung)')")
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('wave_no', '09792654163 (Si Thu Aung)')")
        conn.commit()

init_db()

def register_user(user_id):
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()

def get_setting(key, default=""):
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = cursor.fetchone()
        return row[0] if row else default

def check_user_channel(user_id):
    if user_id == ADMIN_ID: return True
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']: return True
    except Exception:
        pass
    return False

def detect_operator(phone):
    p = ''.join(filter(str.isdigit, phone))
    if p.startswith('959'): p = '0' + p[2:]
    elif not p.startswith('0'): p = '09' + p
    
    if p.startswith(('0975', '0976', '0977', '0978', '0979')): return 'ATOM'
    elif p.startswith(('099', '0995', '0996', '0997', '0998', '0999')): return 'Ooredoo'
    elif p.startswith(('096', '0966', '0967', '0968', '0969', '0965', '0964')): return 'Mytel'
    elif p.startswith(('092', '094', '095', '098', '091')): return 'MPT'
    else: return 'Other'

def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton("✨ နံပါတ်လှများ"), types.KeyboardButton("🍀 Lucky Phone"))
    markup.add(types.KeyboardButton("📡 Operator အလိုက်"), types.KeyboardButton("🛒 Digital အကောင့်များ"))
    markup.add(types.KeyboardButton("🔍 နံပါတ်ရှာမည်"), types.KeyboardButton("📜 မိမိအော်ဒါများ"))
    markup.add(types.KeyboardButton("📞 ဆိုင်နှင့် ဆက်သွယ်ရန်"))
    if user_id == ADMIN_ID: markup.add(types.KeyboardButton("👑 Admin Panel"))
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
    register_user(user_id)
    if not check_user_channel(user_id):
        bot.send_message(message.chat.id, "⚠️ *ကျေးဇူးပြု၍ ကျွန်ုပ်တို့၏ Channel ကို အရင် Join ပေးပါ။*", reply_markup=not_joined_markup(), parse_mode="Markdown")
        return
    bot.send_message(message.chat.id, "✨ *VIP Phone Numbers & Accounts Shop မှ ကြိုဆိုပါတယ်။*", reply_markup=main_menu(user_id), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def verify_join_callback(call):
    user_id = call.from_user.id
    register_user(user_id)
    if check_user_channel(user_id):
        bot.answer_callback_query(call.id, "Channel Join ပြီးသားဖြစ်တာကို စစ်ဆေးတွေ့ရှိရပါပြီ။")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✨ *VIP Phone Numbers & Accounts Shop မှ ကြိုဆိုပါတယ်။*", reply_markup=main_menu(user_id), parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "⚠️ ကျေးဇူးပြု၍ Channel ကို အရင် Join ပေးပါ။", show_alert=True)

def require_channel_join(func):
    def wrapper(message):
        register_user(message.from_user.id)
        if not check_user_channel(message.from_user.id):
            bot.send_message(message.chat.id, "⚠️ ဤစနစ်ကို အသုံးပြုရန် Channel ကို အရင် Join ပါ။", reply_markup=not_joined_markup(), parse_mode="Markdown")
            return
        return func(message)
    return wrapper

@bot.message_handler(func=lambda m: m.text == "✨ နံပါတ်လှများ")
@require_channel_join
def show_pro_numbers(message): show_numbers_by_type(message, "PRO", page=1)

@bot.message_handler(func=lambda m: m.text == "🍀 Lucky Phone")
@require_channel_join
def show_lucky_numbers(message): show_numbers_by_type(message, "LUCKY", page=1)

def show_numbers_by_type(message_or_call, n_type, page=1, is_edit=False):
    offset = (page - 1) * ITEMS_PER_PAGE
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM numbers WHERE num_type=? AND status='AVAILABLE'", (n_type,))
        total_items = cursor.fetchone()[0]

        cursor.execute("SELECT id, phone_number, operator, price FROM numbers WHERE num_type=? AND status='AVAILABLE' LIMIT ? OFFSET ?", (n_type, ITEMS_PER_PAGE, offset))
        rows = cursor.fetchall()
    
    if not rows:
        text = "📭 လောလောဆယ် နံပါတ်များ မရှိသေးပါ။"
        if is_edit: bot.answer_callback_query(message_or_call.id, text, show_alert=True)
        else: bot.send_message(message_or_call.chat.id, text)
        return

    total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
    title_text = "✨ *ရောင်းရန်ရှိသော နံပါတ်လှများ -*" if n_type == "PRO" else "🍀 *ရောင်းရန်ရှိသော Lucky Phone များ -*"

    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        markup.add(types.InlineKeyboardButton(f"📱 {r[1]} ({r[2]}) - {r[3]:,.0f} ကျပ်", callback_data=f"buy_num_{r[0]}"))

    nav_buttons = []
    if page > 1:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ ရှေ့သို့", callback_data=f"pnum_{n_type}_{page-1}"))
    nav_buttons.append(types.InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="ignore"))
    if page < total_pages:
        nav_buttons.append(types.InlineKeyboardButton("နောက်သို့ ➡️", callback_data=f"pnum_{n_type}_{page+1}"))
    
    if len(nav_buttons) > 1:
        markup.row(*nav_buttons)

    chat_id = message_or_call.message.chat.id if is_edit else message_or_call.chat.id
    msg_text = f"{title_text}\n*(စာမျက်နှာ {page}/{total_pages})*"

    if is_edit:
        bot.edit_message_text(msg_text, chat_id, message_or_call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, msg_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("pnum_"))
def paginate_numbers(call):
    parts = call.data.split("_")
    show_numbers_by_type(call, parts[1], page=int(parts[2]), is_edit=True)

@bot.message_handler(func=lambda m: m.text == "📡 Operator အလိုက်")
@require_channel_join
def show_operators(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    for op in ["MPT", "ATOM", "Ooredoo", "Mytel"]:
        markup.add(types.InlineKeyboardButton(op, callback_data=f"op_{op}_1"))
    bot.send_message(message.chat.id, "ကြည့်ရှုလိုသော အော်ပရေတာကို ရွေးချယ်ပါ -", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("op_"))
def filter_by_operator(call):
    if not check_user_channel(call.from_user.id): return
    parts = call.data.split("_")
    op_name = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 1
    offset = (page - 1) * ITEMS_PER_PAGE

    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM numbers WHERE operator=? AND status='AVAILABLE'", (op_name,))
        total_items = cursor.fetchone()[0]

        cursor.execute("SELECT id, phone_number, price, num_type FROM numbers WHERE operator=? AND status='AVAILABLE' LIMIT ? OFFSET ?", (op_name, ITEMS_PER_PAGE, offset))
        rows = cursor.fetchall()
    
    if not rows:
        bot.answer_callback_query(call.id, f"{op_name} နံပါတ်များ မရှိသေးပါ။", show_alert=True)
        return

    total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        tag = "✨" if r[3] == "PRO" else "🍀"
        markup.add(types.InlineKeyboardButton(f"[{tag}] {r[1]} - {r[2]:,.0f} ကျပ်", callback_data=f"buy_num_{r[0]}"))

    nav_buttons = []
    if page > 1:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ ရှေ့သို့", callback_data=f"op_{op_name}_{page-1}"))
    nav_buttons.append(types.InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="ignore"))
    if page < total_pages:
        nav_buttons.append(types.InlineKeyboardButton("နောက်သို့ ➡️", callback_data=f"op_{op_name}_{page+1}"))
    
    if len(nav_buttons) > 1:
        markup.row(*nav_buttons)

    bot.edit_message_text(f"📡 *{op_name}* ရရှိနိုင်သော နံပါတ်များ - *(စာမျက်နှာ {page}/{total_pages})*", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔍 နံပါတ်ရှာမည်")
@require_channel_join
def search_number_start(message):
    msg = bot.send_message(message.chat.id, "🔎 ရှာလိုသော ဂဏန်း (သို့မဟုတ်) ဖုန်းနံပါတ်အစိတ်အပိုင်းကို ရိုက်ထည့်ပါ (ဥပမာ - 777 သို့မဟုတ် 097):")
    bot.register_next_step_handler(msg, process_number_search)

def process_number_search(message):
    if not check_user_channel(message.from_user.id): return
    keyword = message.text.strip()
    
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, phone_number, operator, price, num_type FROM numbers WHERE phone_number LIKE ? AND status='AVAILABLE' LIMIT 10", (f"%{keyword}%",))
        rows = cursor.fetchall()

    if not rows:
        bot.send_message(message.chat.id, f"📭 `{keyword}` ပါဝင်သော နံပါတ်များ မတွေ့ရှိပါ။", reply_markup=main_menu(message.from_user.id), parse_mode="Markdown")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        tag = "✨" if r[4] == "PRO" else "🍀"
        markup.add(types.InlineKeyboardButton(f"[{tag}] {r[1]} ({r[2]}) - {r[3]:,.0f} ကျပ်", callback_data=f"buy_num_{r[0]}"))

    bot.send_message(message.chat.id, f"🔎 `{keyword}` ရှာဖွေတွေ့ရှိမှု ရလဒ်များ -", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🛒 Digital အကောင့်များ")
@require_channel_join
def show_acc_categories(message):
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM accounts WHERE status='AVAILABLE'")
        rows = cursor.fetchall()

    if not rows:
        bot.send_message(message.chat.id, "📭 လောလောဆယ် ရောင်းရန် အကောင့်များ မရှိသေးပါ။")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    for r in rows:
        markup.add(types.InlineKeyboardButton(f"📁 {r[0]}", callback_data=f"cat_{r[0]}_1"))
    bot.send_message(message.chat.id, "🛒 ကြည့်ရှုလိုသော အကောင့် Category ကို ရွေးချယ်ပါ -", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
def filter_acc_by_category(call):
    if not check_user_channel(call.from_user.id): return
    parts = call.data.split("_")
    cat_name = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 1
    offset = (page - 1) * ITEMS_PER_PAGE
    
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM accounts WHERE category=? AND status='AVAILABLE'", (cat_name,))
        total_items = cursor.fetchone()[0]

        cursor.execute("SELECT id, title, price FROM accounts WHERE category=? AND status='AVAILABLE' LIMIT ? OFFSET ?", (cat_name, ITEMS_PER_PAGE, offset))
        rows = cursor.fetchall()

    if not rows:
        bot.answer_callback_query(call.id, f"{cat_name} တွင် အကောင့်များ မရှိသေးပါ။", show_alert=True)
        return

    total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        markup.add(types.InlineKeyboardButton(f"💰 {r[1]} - {r[2]:,.0f} ကျပ်", callback_data=f"buy_acc_{r[0]}"))

    nav_buttons = []
    if page > 1:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ ရှေ့သို့", callback_data=f"cat_{cat_name}_{page-1}"))
    nav_buttons.append(types.InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="ignore"))
    if page < total_pages:
        nav_buttons.append(types.InlineKeyboardButton("နောက်သို့ ➡️", callback_data=f"cat_{cat_name}_{page+1}"))
    
    if len(nav_buttons) > 1:
        markup.row(*nav_buttons)

    bot.edit_message_text(f"📡 *{cat_name}* အမျိုးအစား ရရှိနိုင်သော အကောင့်များ - *(စာမျက်နှာ {page}/{total_pages})*", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "ignore")
def ignore_callback(call):
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_num_"))
def process_buy_num(call):
    if not check_user_channel(call.from_user.id): return
    n_id = call.data.split("_")[2]
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT phone_number, price, status FROM numbers WHERE id=?", (n_id,))
        item = cursor.fetchone()
    
    if not item or item[2] == 'SOLD':
        bot.answer_callback_query(call.id, "ဤနံပါတ် ဝယ်ယူပြီးဖြစ်ပါသည် (သို့) မရှိတော့ပါ။", show_alert=True)
        return

    phone, price, _ = item
    deli = get_setting('deli_fee', '4000')
    kpay = get_setting('kpay_no', '')
    wave = get_setting('wave_no', '')

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ ဝယ်ယူမှု ဖျက်သိမ်းမည်", callback_data="cancel_step"))

    msg = bot.send_message(
        call.message.chat.id,
        f"🎯 နံပါတ် - *{phone}*\n💰 ဈေးနှုန်း - `{price:,.0f}` ကျပ်\n\n"
        f"📦 Deli ခ **`{deli}`** ကျပ်ကို အရင်လွှဲရပါမည်။\n\n"
        f"🔹 *KPay:* `{kpay}`\n🔹 *WavePay:* `{wave}`\n\n"
        f"📝 ငွေလွှဲပြေစာ ပုံ သို့မဟုတ် **နာမည်၊ ဖုန်း၊ လိပ်စာ** အတိအကျ ပို့ပေးပါ -",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, save_order, 'PHONE', phone, price, n_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_acc_"))
def process_buy_acc(call):
    if not check_user_channel(call.from_user.id): return
    acc_id = call.data.split("_")[2]
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title, price, status, category FROM accounts WHERE id=?", (acc_id,))
        item = cursor.fetchone()
    
    if not item or item[2] == 'SOLD':
        bot.answer_callback_query(call.id, "ဤအကောင့် ဝယ်ယူပြီးဖြစ်ပါသည် (သို့) မရှိတော့ပါ။", show_alert=True)
        return

    title, price, _, category = item
    kpay = get_setting('kpay_no', '')
    wave = get_setting('wave_no', '')

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("👨‍💻 Admin ထံ တိုက်ရိုက်ဆက်သွယ်ဝယ်ယူရန်", url=f"https://t.me/starmobile63956_admin"),
        types.InlineKeyboardButton("❌ ပယ်ဖျက်မည်", callback_data="cancel_step")
    )

    bot.edit_message_text(
        f"🛒 *Digital Account ဝယ်ယူရန်*\n\n"
        f"🎯 အကောင့်အမျိုးအစား: *{title}* ({category})\n"
        f"💰 ကျသင့်ငွေ: `{price:,.0f}` ကျပ်\n\n"
        f"🔹 *KPay:* `{kpay}`\n🔹 *WavePay:* `{wave}`\n\n"
        f"📌 ငွေလွှဲပြီးပါက အောက်ပါခလုတ်ကိုနှိပ်၍ Admin ဆီသို့ ငွေလွှဲပြေစာနှင့်တကွ တိုက်ရိုက်ဆက်သွယ်ဝယ်ယူနိုင်ပါသည် -",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "cancel_step")
def user_cancel_step(call):
    bot.clear_step_handler_by_chat_id(call.message.chat.id)
    bot.edit_message_text("❌ *ဝယ်ယူမှုကို ဖျက်သိမ်းလိုက်ပါပြီ။*", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.send_message(call.message.chat.id, "အခြား ပစ္စည်းများကို ရွေးချယ်နိုင်ပါသည်။", reply_markup=main_menu(call.from_user.id))

def save_order(message, item_type, title, price, ref_id):
    if not check_user_channel(message.from_user.id): return
    
    menu_buttons = ["✨ နံပါတ်လှများ", "🍀 Lucky Phone", "📡 Operator အလိုက်", "🛒 Digital အကောင့်များ", "🔍 နံပါတ်ရှာမည်", "📜 မိမိအော်ဒါများ", "📞 ဆိုင်နှင့် ဆက်သွယ်ရန်", "👑 Admin Panel", "/start"]
    if message.text in menu_buttons:
        bot.send_message(message.chat.id, "⚠️ ဝယ်ယူမှုကို ပယ်ဖျက်လိုက်ပါပြီ။", reply_markup=main_menu(message.from_user.id))
        return

    uid = message.from_user.id
    user_name = message.from_user.first_name
    username = message.from_user.username
    
    photo_file_id = None
    info_text = message.text or "ငွေလွှဲပြေစာ ဓာတ်ပုံ ပေးပို့ထားပါသည်"

    if message.photo:
        photo_file_id = message.photo[-1].file_id
        if message.caption:
            info_text = f"📷 Photo + Caption: {message.caption}"

    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO orders (user_id, customer_name, item_type, chosen_item, price, contact_info, ref_id, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING')",
            (uid, user_name, item_type, title, price, info_text, ref_id)
        )
        oid = cursor.lastrowid
        
        if item_type == 'PHONE':
            cursor.execute("UPDATE numbers SET status='SOLD' WHERE id=?", (ref_id,))
        else:
            cursor.execute("UPDATE accounts SET status='SOLD' WHERE id=?", (ref_id,))
        conn.commit()

    bot.send_message(message.chat.id, f"🎉 *အော်ဒါတင်ခြင်း အောင်မြင်ပါသည်။*\n\n🛒 မှာယူသည့်ပစ္စည်း: `{title}`\n📍 အချက်အလက်: {info_text}\n\nAdmin မှ စစ်ဆေးအတည်ပြုပေးပါမည်။", reply_markup=main_menu(uid), parse_mode="Markdown")
    
    user_link = f"@{username}" if username else f"ID: {uid}"
    admin_text = (
        f"🚨 *အော်ဒါအသစ် ရောက်ရှိပါပြီ!*\n\n"
        f"🆔 Order ID: #{oid}\n"
        f"👤 ဝယ်ယူသူ: {user_name} ({user_link})\n"
        f"🛍 အမျိုးအစား: {item_type}\n"
        f"🎯 မှာယူသည့်အရာ: {title}\n"
        f"💰 ဈေးနှုန်း: {price:,.0f} ကျပ်\n"
        f"📝 အချက်အလက်: {info_text}"
    )
    
    admin_markup = types.InlineKeyboardMarkup(row_width=2)
    admin_markup.add(
        types.InlineKeyboardButton("✅ အတည်ပြုမည် (Approve)", callback_data=f"approve_{oid}"),
        types.InlineKeyboardButton("❌ ပယ်ဖျက်မည် (Reject)", callback_data=f"reject_{oid}")
    )

    try:
        if photo_file_id:
            bot.send_photo(ADMIN_ID, photo_file_id, caption=admin_text, reply_markup=admin_markup, parse_mode="Markdown")
        else:
            bot.send_message(ADMIN_ID, admin_text, reply_markup=admin_markup, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Admin ထံ အော်ဒါပို့ရာတွင် အမှား: {e}")

@bot.message_handler(func=lambda m: m.text == "👑 Admin Panel" and m.from_user.id == ADMIN_ID)
def admin_panel_main(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ နံပါတ်အသစ်ထည့်ရန်", callback_data="adm_add_num"),
        types.InlineKeyboardButton("➕ အကောင့်အသစ်ထည့်ရန်", callback_data="adm_add_acc"),
        types.InlineKeyboardButton("📢 Broadcast ပို့ရန်", callback_data="adm_broadcast")
    )
    bot.send_message(message.chat.id, "👑 *Admin Control Panel သို့ ကြိုဆိုပါသည်။*", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_") and call.from_user.id == ADMIN_ID)
def admin_callbacks(call):
    action = call.data.split("_")[1]
    if action == "add" and call.data.split("_")[2] == "num":
        msg = bot.send_message(
            call.message.chat.id, 
            "နံပါတ်အသစ် ထည့်ရန် ပုံစံအတိုင်း ရိုက်ပို့ပါ:\n\n"
            "`နံပါတ်, ဈေးနှုန်း, အမျိုးအစား(PRO/LUCKY)`\n"
            "ဥပမာ: `09777777777, 50000, PRO`", 
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, save_new_number_admin)
    elif action == "add" and call.data.split("_")[2] == "acc":
        msg = bot.send_message(call.message.chat.id, "အကောင့်အသစ် ထည့်ရန် ပုံစံအတိုင်း ရိုက်ပို့ပါ:\n\n`Category, Title, ဈေးနှုန်း, အကောင့်အချက်အလက်(Details)`\nဥပမာ: `Netflix, 1 Month Premium, 5000, email:abc pass:123`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, save_new_acc_admin)
    elif action == "broadcast":
        msg = bot.send_message(call.message.chat.id, "📢 အသုံးပြုသူအားလုံးဆီ ပို့လိုသော ကြေညာချက် စာသားကို ရိုက်ပို့ပါ:")
        bot.register_next_step_handler(msg, process_broadcast)

def save_new_number_admin(message):
    try:
        parts = [p.strip() for p in message.text.split(',')]
        phone, price, n_type = parts[0], float(parts[1]), parts[2].upper()
        op = detect_operator(phone)
        
        with sqlite3.connect('vip_shop.db') as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO numbers (phone_number, operator, price, num_type) VALUES (?, ?, ?, ?)", (phone, op, price, n_type))
            conn.commit()
        bot.send_message(message.chat.id, f"✅ နံပါတ်အသစ် ထည့်သွင်းခြင်း အောင်မြင်ပါသည်။ (Detected Operator: {op})")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ အမှားအယွင်းရှိပါသည်: {e}")

def save_new_acc_admin(message):
    try:
        parts = [p.strip() for p in message.text.split(',')]
        cat, title, price, details = parts[0], parts[1], float(parts[2]), parts[3]
        
        with sqlite3.connect('vip_shop.db') as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO accounts (category, title, price, details) VALUES (?, ?, ?, ?)", (cat, title, price, details))
            conn.commit()
        bot.send_message(message.chat.id, f"✅ အကောင့်အသစ် ထည့်သွင်းခြင်း အောင်မြင်ပါသည်။")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ အမှားအယွင်းရှိပါသည်: {e}")

def process_broadcast(message):
    text = message.text
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
    
    success = 0
    for u in users:
        try:
            bot.send_message(u[0], f"📢 *ကြေညာချက်*\n\n{text}", parse_mode="Markdown")
            success += 1
        except:
            pass
    bot.send_message(message.chat.id, f"✅ Broadcast ပို့ခြင်း ပြီးစီးပါပြီ။ အောင်မြင်သူဦးရေ: {success}")

@bot.callback_query_handler(func=lambda call: (call.data.startswith("approve_") or call.data.startswith("reject_")) and call.from_user.id == ADMIN_ID)
def handle_order_action(call):
    parts = call.data.split("_")
    action, oid = parts[0], parts[1]
    
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, item_type, ref_id, chosen_item FROM orders WHERE id=?", (oid,))
        order = cursor.fetchone()
        
    if not order:
        bot.answer_callback_query(call.id, "အော်ဒါ မတွေ့ရှိတော့ပါ။", show_alert=True)
        return

    uid, item_type, ref_id, chosen_item = order

    if action == "approve":
        with sqlite3.connect('vip_shop.db') as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE orders SET status='APPROVED' WHERE id=?", (oid,))
            conn.commit()
            
        bot.edit_message_caption(f"{call.message.caption}\n\n✅ **Status: APPROVED (အတည်ပြုပြီး)**", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        
        delivery_extra = ""
        if item_type == 'ACCOUNT':
            with sqlite3.connect('vip_shop.db') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT details FROM accounts WHERE id=?", (ref_id,))
                acc = cursor.fetchone()
                if acc and acc[0]:
                    delivery_extra = f"\n\n🔑 *အကောင့်အချက်အလက် (Auto-Delivery):*\n`{acc[0]}`"

        bot.send_message(uid, f"🎉 သင့်ရဲ့ အော်ဒါ (#{oid}) - *{chosen_item}* ကို Admin မှ အတည်ပြုပေးလိုက်ပါပြီ။{delivery_extra}", parse_mode="Markdown")
    else:
        with sqlite3.connect('vip_shop.db') as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE orders SET status='REJECTED' WHERE id=?", (oid,))
            if item_type == 'PHONE':
                cursor.execute("UPDATE numbers SET status='AVAILABLE' WHERE id=?", (ref_id,))
            else:
                cursor.execute("UPDATE accounts SET status='AVAILABLE' WHERE id=?", (ref_id,))
            conn.commit()
            
        bot.edit_message_caption(f"{call.message.caption}\n\n❌ **Status: REJECTED (ပယ်ဖျက်လိုက်သည်)**", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        bot.send_message(uid, f"❌ သင့်ရဲ့ အော်ဒါ (#{oid}) - *{chosen_item}* မှာ ငွေလွှဲပြေစာ မမှန်ကန်မှု (သို့) အခြားအကြောင်းကြောင့် ပယ်ဖျက်ခံလိုက်ရပါသည်။", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📜 မိမိအော်ဒါများ")
@require_channel_join
def show_my_orders(message):
    uid = message.from_user.id
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, chosen_item, price, status, date FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 5", (uid,))
        rows = cursor.fetchall()

    if not rows:
        bot.send_message(message.chat.id, "📭 လောလောဆယ် မှာယူထားသော အော်ဒါမှတ်တမ်း မရှိသေးပါ။")
        return

    text = "📜 *သင်၏ နောက်ဆုံး မှာယူထားသော အော်ဒါများ -*\n\n"
    for r in rows:
        status_str = "⏳ စစ်ဆေးဆဲ" if r[3] == 'PENDING' else ("✅ ပြီးစီး" if r[3] == 'APPROVED' else "❌ ပယ်ဖျက်ပြီး")
        text += f"🆔 Order #{r[0]}\n🛍 ပစ္စည်း: {r[1]}\n💰 ဈေးနှုန်း: {r[2]:,.0f} ကျပ်\n📌 အခြေအနေ: {status_str}\n⏱ အချိန်: {r[4]}\n---------------------------\n"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📞 ဆိုင်နှင့် ဆက်သွယ်ရန်")
@require_channel_join
def contact_shop(message):
    text = (
        "📞 *ဆိုင်နှင့် ဆက်သွယ်ရန်*\n\n"
        f"📢 Telegram Channel: {CHANNEL_USERNAME}\n"
        "👨‍💻 Admin ဆက်သွယ်ရန်: @starmobile63956_admin"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

print("VIP Shop Bot is running successfully...")
bot.infinity_polling()
