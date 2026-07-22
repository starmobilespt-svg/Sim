import sqlite3
import telebot
from telebot import types
import csv
import io
import logging
import os
import threading
from flask import Flask

# Logging စနစ်
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "8753076212:AAHBn4zvIYrrSr3XJTumF6ZgHRSqQqWbT8U"
ADMIN_ID = 8668319365
CHANNEL_USERNAME = "@starmobile63956"

bot = telebot.TeleBot(TOKEN)

# ----------------------------------------------------
# Render မပိတ်သွားစေရန် Flask Web Server ထည့်ခြင်း
# ----------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "VIP Phone Shop Bot is running 24/7 on Render!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ----------------------------------------------------
# Database 
# ----------------------------------------------------
def init_db():
    conn = sqlite3.connect('vip_shop.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS numbers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number TEXT,
            operator TEXT,
            price REAL,
            num_type TEXT
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
    conn.close()

init_db()

def get_setting(key, default=""):
    conn = sqlite3.connect('vip_shop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default

def set_setting(key, value):
    conn = sqlite3.connect('vip_shop.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def detect_operator(phone):
    p = ''.join(filter(str.isdigit, phone))
    if p.startswith('959'):
        p = '0' + p[2:]
    elif not p.startswith('0'):
        p = '09' + p
    if p.startswith(('0975', '0976', '0977', '0978', '0979')): return 'ATOM'
    elif p.startswith(('099', '0995', '0996', '0997', '0998', '0999')): return 'Ooredoo'
    elif p.startswith(('096', '0966', '0967', '0968', '0969', '0965', '0964')): return 'Mytel'
    elif p.startswith(('092', '094', '095', '098', '091')): return 'MPT'
    else: return 'Other'

def check_user_channel(user_id):
    if user_id == ADMIN_ID: return True
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']: return True
    except Exception:
        pass
    return False

def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton("✨ နံပါတ်လှများကြည့်မည်"), types.KeyboardButton("🍀 Lucky Phone ကြည့်မည်"))
    markup.add(types.KeyboardButton("📡 Operator အလိုက်ကြည့်မည်"), types.KeyboardButton("🔍 နံပါတ်ရှာမည်"))
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
    if not check_user_channel(user_id):
        bot.send_message(message.chat.id, "⚠️ *ကျေးဇူးပြု၍ ကျွန်ုပ်တို့၏ Channel ကို အရင် Join ပေးပါ။*", reply_markup=not_joined_markup(), parse_mode="Markdown")
        return
    bot.send_message(message.chat.id, "✨ *Phone Numbers Sales Bot မှ ကြိုဆိုပါတယ်။*", reply_markup=main_menu(user_id), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def verify_join_callback(call):
    user_id = call.from_user.id
    if check_user_channel(user_id):
        bot.answer_callback_query(call.id, "Channel Join ပြီးသားဖြစ်တာကို စစ်ဆေးတွေ့ရှိရပါပြီ။")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✨ *Phone Numbers Sales Bot မှ ကြိုဆိုပါတယ်။*", reply_markup=main_menu(user_id), parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "⚠️ ကျေးဇူးပြု၍ Channel ကို အရင် Join ပေးပါ။", show_alert=True)

def require_channel_join(func):
    def wrapper(message):
        if not check_user_channel(message.from_user.id):
            bot.send_message(message.chat.id, "⚠️ ဤစနစ်ကို အသုံးပြုရန် Channel ကို အရင် Join ပါ။", reply_markup=not_joined_markup(), parse_mode="Markdown")
            return
        return func(message)
    return wrapper

@bot.message_handler(func=lambda m: m.text == "✨ နံပါတ်လှများကြည့်မည်")
@require_channel_join
def show_pro_numbers(message): show_numbers_by_type(message, "PRO", "✨ ရောင်းရန်ရှိသော နံပါတ်လှများ -")

@bot.message_handler(func=lambda m: m.text == "🍀 Lucky Phone ကြည့်မည်")
@require_channel_join
def show_lucky_numbers(message): show_numbers_by_type(message, "LUCKY", "🍀 ရောင်းရန်ရှိသော Lucky Phone များ -")

def show_numbers_by_type(message, n_type, title_text):
    conn = sqlite3.connect('vip_shop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, phone_number, operator, price FROM numbers WHERE num_type=?", (n_type,))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        bot.send_message(message.chat.id, "📭 လောလောဆယ် နံပါတ်များ မရှိသေးပါ။")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        markup.add(types.InlineKeyboardButton(f"📱 {r[1]} ({r[2]}) - {r[3]:,.0f} ကျပ်", callback_data=f"buy_{r[0]}"))
    bot.send_message(message.chat.id, title_text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📡 Operator အလိုက်ကြည့်မည်")
@require_channel_join
def show_operators(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    for op in ["MPT", "ATOM", "Ooredoo", "Mytel"]:
        markup.add(types.InlineKeyboardButton(op, callback_data=f"op_{op}"))
    bot.send_message(message.chat.id, "ကြည့်ရှုလိုသော အော်ပရေတာကို ရွေးချယ်ပါ -", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("op_"))
def filter_by_operator(call):
    if not check_user_channel(call.from_user.id):
        bot.answer_callback_query(call.id, "⚠️ Channel Join ပါ။", show_alert=True)
        return
    op_name = call.data.split("_")[1]
    conn = sqlite3.connect('vip_shop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, phone_number, price, num_type FROM numbers WHERE operator=?", (op_name,))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        bot.answer_callback_query(call.id, f"{op_name} နံပါတ်များ မရှိသေးပါ။")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        tag = "✨" if r[3] == "PRO" else "🍀"
        markup.add(types.InlineKeyboardButton(f"[{tag}] {r[1]} - {r[2]:,.0f} ကျပ်", callback_data=f"buy_{r[0]}"))
    bot.edit_message_text(f"📡 *{op_name}* ရရှိနိုင်သော နံပါတ်များ -", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔍 နံပါတ်ရှာမည်")
@require_channel_join
def search_number(message):
    msg = bot.send_message(message.chat.id, "🔍 သင်ရှာဖွေလိုသော ဂဏန်းကို ရိုက်ထည့်ပါ (ဥပမာ - 777)")
    bot.register_next_step_handler(msg, process_search)

def process_search(message):
    if not check_user_channel(message.from_user.id): return
    kw = message.text.strip()
    conn = sqlite3.connect('vip_shop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, phone_number, operator, price, num_type FROM numbers WHERE phone_number LIKE ?", (f'%{kw}%',))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        bot.send_message(message.chat.id, f"❌ `{kw}` ပါဝင်သော နံပါတ်များ ရှာမတွေ့ပါ။", parse_mode="Markdown")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        tag = "✨" if r[4] == "PRO" else "🍀"
        markup.add(types.InlineKeyboardButton(f"[{tag}] {r[1]} ({r[2]}) - {r[3]:,.0f} ကျပ်", callback_data=f"buy_{r[0]}"))
    bot.send_message(message.chat.id, f"🔍 ရှာတွေ့သော နံပါတ်များ -", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def process_buy(call):
    if not check_user_channel(call.from_user.id):
        bot.answer_callback_query(call.id, "⚠️ Channel Join ပါ။", show_alert=True)
        return
    n_id = call.data.split("_")[1]
    conn = sqlite3.connect('vip_shop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT phone_number, price FROM numbers WHERE id=?", (n_id,))
    item = cursor.fetchone()
    conn.close()
    if not item:
        bot.answer_callback_query(call.id, "ဤနံပါတ် မရှိတော့ပါ။", show_alert=True)
        return
    phone, price = item
    deli = get_setting('deli_fee', '4000')
    kpay = get_setting('kpay_no', '')
    wave = get_setting('wave_no', '')
    
    msg = bot.send_message(
        call.message.chat.id,
        f"🎯 နံပါတ် - *{phone}*\n💰 ဈေးနှုန်း - `{price:,.0f}` ကျပ်\n\n"
        f"📦 အိမ်ရောက်ငွေချေ (COD) ဖြင့် ပို့မည်ဖြစ်ပြီး Deli ခ **`{deli}`** ကျပ်ကို အရင်လွှဲရပါမည်။\n\n"
        f"🔹 *KPay:* `{kpay}`\n🔹 *WavePay:* `{wave}`\n\n"
        f"📝 Deli ခလွှဲပြီးပါက **နာမည်၊ ဖုန်း၊ လိပ်စာ** အတိအကျ ပို့ပေးပါ -\n*(ဥပမာ - မောင်မောင်၊ 09792654163၊ ရန်ကုန်)*",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, save_order, phone, price, n_id)

def save_order(message, phone, price, n_id):
    if not check_user_channel(message.from_user.id): return
    info = message.text
    uid = message.from_user.id
    deli = get_setting('deli_fee', '4000')
    conn = sqlite3.connect('vip_shop.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (user_id, customer_name, chosen_number, price, contact_info) VALUES (?, ?, ?, ?, ?)", (uid, message.from_user.first_name, phone, price, info))
    oid = cursor.lastrowid
    cursor.execute("DELETE FROM numbers WHERE id=?", (n_id,))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, f"🎉 အော်ဒါတင်ခြင်း အောင်မြင်ပါသည်။\n📱 {phone}\n📍 {info}\nAdmin ထံ ဆက်သွယ်ပေးပါ။", reply_markup=main_menu(uid), parse_mode="Markdown")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ ပို့ပြီးပါပြီ (ဖျက်မည်)", callback_data=f"done_{oid}"))
    try:
        bot.send_message(ADMIN_ID, f"🚨 အော်ဒါအသစ်!\n👤 {message.from_user.first_name}\n📱 `{phone}`\n📍 {info}", reply_markup=markup, parse_mode="Markdown")
    except Exception: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("done_"))
def mark_order_done(call):
    if call.from_user.id != ADMIN_ID: return
    oid = call.data.split("_")[1]
    conn = sqlite3.connect('vip_shop.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM orders WHERE id=?", (oid,))
    conn.commit()
    conn.close()
    bot.edit_message_text(f"{call.message.text}\n\n✅ အော်ဒါ ပြီးစီးသွားပါပြီ။", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👑 Admin Panel")
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    bot.send_message(message.chat.id, "👑 *Admin Panel*\n\nCommands:\n`/add_num pro/lucky [နံပါတ်] [ဈေးနှုန်း]`\n`/list`\n`/del_num [ID]`\n`/orders`\n`/set_deli [ငွေ]`\n`/set_kpay [နံပါတ်]`\n`/set_wave [နံပါတ်]`", parse_mode="Markdown")

@bot.message_handler(commands=['set_deli'])
def set_deli(m): 
    if m.from_user.id == ADMIN_ID: set_setting('deli_fee', m.text.split(maxsplit=1)[1]); bot.send_message(m.chat.id, "✅ ပြောင်းပြီးပြီ။")

@bot.message_handler(commands=['set_kpay'])
def set_k(m): 
    if m.from_user.id == ADMIN_ID: set_setting('kpay_no', m.text.split(maxsplit=1)[1]); bot.send_message(m.chat.id, "✅ ပြောင်းပြီးပြီ။")

@bot.message_handler(commands=['set_wave'])
def set_w(m): 
    if m.from_user.id == ADMIN_ID: set_setting('wave_no', m.text.split(maxsplit=1)[1]); bot.send_message(m.chat.id, "✅ ပြောင်းပြီးပြီ။")

@bot.message_handler(commands=['add_num'])
def add_num(m):
    if m.from_user.id != ADMIN_ID: return
    try:
        p = m.text.split()
        t = "PRO" if p[1].lower() in ['pro', 'vip'] else "LUCKY"
        price = float(p[-1])
        phone = " ".join(p[2:-1])
        op = detect_operator(phone)
        conn = sqlite3.connect('vip_shop.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO numbers (phone_number, operator, price, num_type) VALUES (?, ?, ?, ?)", (phone, op, price, t))
        conn.commit()
        conn.close()
        bot.send_message(m.chat.id, f"✅ ထည့်ပြီးပါပြီ: {phone}")
    except Exception: bot.send_message(m.chat.id, "❌ ပုံစံမှားနေပါသည်။ ဥပမာ: `/add_num pro 09777777777 1500000`", parse_mode="Markdown")

@bot.message_handler(commands=['list'])
def list_n(m):
    if m.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect('vip_shop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, phone_number, operator, price FROM numbers")
    rows = cursor.fetchall()
    conn.close()
    if not rows: bot.send_message(m.chat.id, "မရှိပါ။"); return
    text = "📋 စာရင်း:\n" + "\n".join([f"ID: {r[0]} | {r[1]} | {r[3]:,.0f}" for r in rows])
    bot.send_message(m.chat.id, text)

@bot.message_handler(commands=['del_num'])
def del_n(m):
    if m.from_user.id != ADMIN_ID: return
    try:
        nid = m.text.split()[1]
        conn = sqlite3.connect('vip_shop.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM numbers WHERE id=?", (nid,))
        conn.commit()
        conn.close()
        bot.send_message(m.chat.id, f"✅ ဖျက်ပြီးပါပြီ ID: {nid}")
    except Exception: bot.send_message(m.chat.id, "Error")

@bot.message_handler(commands=['orders'])
def exp_orders(m):
    if m.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect('vip_shop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT date, customer_name, chosen_number, price, contact_info FROM orders")
    rows = cursor.fetchall()
    conn.close()
    if not rows: bot.send_message(m.chat.id, "မရှိပါ။"); return
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Name", "Phone", "Price", "Info"])
    for r in rows: writer.writerow(r)
    bio = io.BytesIO(output.getvalue().encode('utf-8-sig'))
    bio.name = 'orders.csv'
    bot.send_document(m.chat.id, bio)

@bot.message_handler(func=lambda m: m.text == "📞 ဆိုင်နှင့် ဆက်သွယ်ရန်")
@require_channel_join
def contact(m):
    bot.send_message(m.chat.id, "📞 ဖုန်း: `09 792 654 163`\n💬 Telegram: @orange310199", parse_mode="Markdown")

# ----------------------------------------------------
# Main Execution (Flask + Telegram Bot)
# ----------------------------------------------------
def main():
    threading.Thread(target=run_web_server, daemon=True).start()
    print("🤖 Phone Shop Bot is running 24/7...")
    bot.infinity_polling()

if __name__ == '__main__':
    main()
