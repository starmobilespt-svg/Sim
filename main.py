import os
import sqlite3
import telebot
from telebot import types
import math
import logging
import threading
from flask import Flask
import time
import requests

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "8753076212:AAHBn4zvIYrrSr3XJTumF6ZgHRSqQqWbT8U"
ADMIN_ID = 8668319365
CHANNEL_USERNAME = "@starmobile63956"
ITEMS_PER_PAGE = 5

bot = telebot.TeleBot(TOKEN)

# Admin က Restore ပြုလုပ်ရန် စောင့်ဆိုင်းနေသော State
waiting_for_restore = {}

# 🌐 Flask Server & Keep Alive Ping (Render Free 24/7 Run ရန်)
app = Flask(__name__)
PORT = int(os.environ.get("PORT", 10000))

@app.route('/')
def home():
    return "VIP Bot Running 24/7"

def run_web_server():
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

threading.Thread(target=run_web_server, daemon=True).start()

def keep_alive_ping():
    time.sleep(10)
    while True:
        try:
            requests.get("http://127.0.0.1:" + str(PORT))
        except Exception:
            pass
        time.sleep(14 * 60)

threading.Thread(target=keep_alive_ping, daemon=True).start()

# 🗄️ Database တည်ဆောက်ခြင်း
def init_db():
    with sqlite3.connect('vip_shop.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS numbers 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, phone_number TEXT, operator TEXT, price REAL, num_type TEXT, status TEXT DEFAULT 'AVAILABLE')''')
        c.execute('''CREATE TABLE IF NOT EXISTS orders 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, customer_name TEXT, chosen_number TEXT, price REAL, contact_info TEXT, ref_id INTEGER, status TEXT DEFAULT 'PENDING', date TIMESTAMP DEFAULT (datetime('now', 'localtime')))''')
        c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_name TEXT)''')
        conn.commit()

init_db()

def register_user(user_id, first_name):
    with sqlite3.connect('vip_shop.db') as conn:
        conn.cursor().execute("INSERT OR IGNORE INTO users (user_id, first_name) VALUES (?, ?)", (user_id, first_name))
        conn.commit()

def detect_operator(phone):
    p = ''.join(filter(str.isdigit, phone))
    if p.startswith('959'): p = '0' + p[2:]
    elif not p.startswith('0'): p = '09' + p
        
    if p.startswith(('0975', '0976', '0977', '0978', '0979')): return 'ATOM'
    elif p.startswith(('099', '0995', '0996', '0997', '0998', '0999')): return 'Ooredoo'
    elif p.startswith(('096', '0966', '0967', '0968', '0969', '0965', '0964')): return 'Mytel'
    elif p.startswith(('092', '094', '095', '098', '091')): return 'MPT'
    else: return 'Other'

def check_user_channel(user_id):
    if user_id == ADMIN_ID: return True
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if m.status in ['member', 'administrator', 'creator']: return True
    except Exception: pass
    return False

def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("✨ နံပါတ်လှများကြည့်မည်", "🍀 Lucky Phone ကြည့်မည်")
    markup.add("📡 Operator အလိုက်ကြည့်မည်", "📞 ဆိုင်နှင့် ဆက်သွယ်ရန်")
    if user_id == ADMIN_ID: markup.add("👑 Admin Panel")
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
    uid = message.from_user.id
    register_user(uid, message.from_user.first_name)
    if not check_user_channel(uid):
        bot.send_message(message.chat.id, "⚠️ *Channel ကို အရင် Join ပေးပါ။*", reply_markup=not_joined_markup(), parse_mode="Markdown")
        return
    bot.send_message(message.chat.id, "✨ *VIP Shop Bot မှ ကြိုဆိုပါတယ်။*", reply_markup=main_menu(uid), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def verify_join_callback(call):
    uid = call.from_user.id
    register_user(uid, call.from_user.first_name)
    if check_user_channel(uid):
        bot.answer_callback_query(call.id, "ကျေးဇူးတင်ပါတယ်။")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✨ *VIP Shop Bot မှ ကြိုဆိုပါတယ်။*", reply_markup=main_menu(uid), parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "⚠️ Channel ကို အရင် Join ပေးပါ။", show_alert=True)

def require_channel_join(func):
    def wrapper(message):
        if not check_user_channel(message.from_user.id):
            bot.send_message(message.chat.id, "⚠️ Channel ကို အရင် Join ပေးပါ။", reply_markup=not_joined_markup(), parse_mode="Markdown")
            return
        return func(message)
    return wrapper

# 👑 ADMIN PANEL & CONTROL BUTTONS
@bot.message_handler(func=lambda m: m.text == "👑 Admin Panel")
def show_admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    text = "👑 **Admin Control Panel**\n\n" + \
           "အောက်ပါ Button များမှတစ်ဆင့် လွယ်ကူစွာ စီမံခန့်ခွဲနိုင်ပါသည်။\n\n" + \
           "📌 **နံပါတ်အသစ်ထည့်ရန် (Command):**\n" + \
           "`/addnum ဖုန်းနံပါတ်, ဈေးနှုန်း, အမျိုးအစား`\n" + \
           "*(ဥပမာ: `/addnum 09 777 888 999, 150000, PRO`)*\n\n" + \
           "📌 **Broadcast စာပို့ရန် (Command):**\n" + \
           "`/broadcast စာသား`"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📦 အော်ဒါများကြည့်ရန် / Cancel လုပ်ရန်", callback_data="admin_view_orders"),
        types.InlineKeyboardButton("📱 ဖုန်းနံပါတ်များကြည့်ရန် / ဖျက်ရန်", callback_data="admin_view_numbers"),
        types.InlineKeyboardButton("💾 Database Backup ယူမည်", callback_data="admin_do_backup"),
        types.InlineKeyboardButton("🔄 Database Restore လုပ်မည်", callback_data="admin_start_restore")
    )
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

# 👑 ADMIN: အော်ဒါများကြည့်ရန် နှင့် Cancel လုပ်ရန်
@bot.callback_query_handler(func=lambda call: call.data == "admin_view_orders")
def admin_view_orders(call):
    if call.from_user.id != ADMIN_ID: return
    with sqlite3.connect('vip_shop.db') as conn:
        rows = conn.cursor().execute("SELECT id, customer_name, chosen_number, price, contact_info, user_id FROM orders WHERE status='PENDING'").fetchall()
    
    if not rows:
        bot.answer_callback_query(call.id, "လောလောဆယ် PENDING အော်ဒါ မရှိပါ။", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    for r in rows:
        txt = "📦 **အော်ဒါနံပါတ်:** #ORD-" + "{:03d}".format(r[0]) + "\n" + \
              "👤 **ဝယ်သူ:** " + str(r[1]) + " (ID: `" + str(r[5]) + "`)\n" + \
              "📱 **မှာယူသည့်နံပါတ်:** `" + str(r[2]) + "`\n" + \
              "💰 **ကျသင့်ငွေ:** " + "{:,.0f}".format(r[3]) + " ကျပ်\n" + \
              "📍 **လိပ်စာ:** " + str(r[4])
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ ဤအော်ဒါကို Cancel မည် (နံပါတ်ပြန်ဖွင့်မည်)", callback_data="admin_cancel_ord_" + str(r[0])))
        bot.send_message(call.message.chat.id, txt, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_cancel_ord_"))
def admin_cancel_order(call):
    if call.from_user.id != ADMIN_ID: return
    oid = int(call.data.split("_")[3])
    with sqlite3.connect('vip_shop.db') as conn:
        c = conn.cursor()
        ord_data = c.execute("SELECT ref_id, user_id, chosen_number FROM orders WHERE id=?", (oid,)).fetchone()
        if ord_data:
            ref_id, user_id, phone = ord_data
            if ref_id:
                c.execute("UPDATE numbers SET status='AVAILABLE' WHERE id=?", (ref_id,))
            c.execute("DELETE FROM orders WHERE id=?", (oid,))
            conn.commit()
            
            bot.answer_callback_query(call.id, "အော်ဒါကို ပယ်ဖျက်လိုက်ပါပြီ။", show_alert=True)
            bot.edit_message_text("❌ **အော်ဒါ #ORD-" + "{:03d}".format(oid) + " ကို Admin မှ Cancel လိုက်ပါသည်။**", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            
            # User ထံ အကြောင်းကြားရန်
            try:
                bot.send_message(user_id, "ℹ️ သင်၏ အော်ဒါ #ORD-" + "{:03d}".format(oid) + " (`" + str(phone) + "`) ကို Admin မှ ပယ်ဖျက်လိုက်ပါပြီ။")
            except Exception: pass

# 👑 ADMIN: မှားထည့်ထားသော ဖုန်းနံပါတ်များ ဖျက်ရန်
@bot.callback_query_handler(func=lambda call: call.data == "admin_view_numbers")
def admin_view_numbers(call):
    if call.from_user.id != ADMIN_ID: return
    with sqlite3.connect('vip_shop.db') as conn:
        rows = conn.cursor().execute("SELECT id, phone_number, operator, price, status FROM numbers ORDER BY id DESC LIMIT 10").fetchall()
    
    if not rows:
        bot.answer_callback_query(call.id, "နံပါတ် မရှိသေးပါ။", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        status_txt = "AVAILABLE" if r[4] == 'AVAILABLE' else "SOLD"
        btn_txt = "📱 " + str(r[1]) + " (" + str(r[2]) + ") - " + "{:,.0f}".format(r[3]) + " ကျပ် [" + status_txt + "]"
        markup.add(types.InlineKeyboardButton("🗑️ ဖျက်မည်: " + str(r[1]), callback_data="admin_del_num_" + str(r[0])))
    
    bot.send_message(call.message.chat.id, "📱 **နောက်ဆုံးထည့်ထားသော နံပါတ် (၁၀) ခု -**\n*(ဖျက်လိုပါက အောက်ပါ Button ကို နှိပ်ပါ)*", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_del_num_"))
def admin_delete_number(call):
    if call.from_user.id != ADMIN_ID: return
    nid = int(call.data.split("_")[3])
    with sqlite3.connect('vip_shop.db') as conn:
        c = conn.cursor()
        num = c.execute("SELECT phone_number FROM numbers WHERE id=?", (nid,)).fetchone()
        if num:
            c.execute("DELETE FROM numbers WHERE id=?", (nid,))
            conn.commit()
            bot.answer_callback_query(call.id, "နံပါတ် " + str(num[0]) + " ကို ဖျက်လိုက်ပါပြီ။", show_alert=True)
            bot.delete_message(call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "နံပါတ် မတွေ့ရှိပါ။", show_alert=True)

# 👑 ADMIN: BACKUP & RESTORE BUTTONS
@bot.callback_query_handler(func=lambda call: call.data == "admin_do_backup")
def callback_admin_backup(call):
    if call.from_user.id != ADMIN_ID: return
    try:
        with open('vip_shop.db', 'rb') as f:
            bot.send_document(call.message.chat.id, f, caption="📦 Database Backup ဖိုင်ရပါပြီ။")
            bot.answer_callback_query(call.id, "Backup ဖိုင် ပို့ပေးလိုက်ပါပြီ။")
    except Exception as e:
        bot.send_message(call.message.chat.id, "❌ Error: " + str(e))

@bot.callback_query_handler(func=lambda call: call.data == "admin_start_restore")
def callback_admin_start_restore(call):
    if call.from_user.id != ADMIN_ID: return
    waiting_for_restore[ADMIN_ID] = True
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "📥 **Database Restore ပြုလုပ်ရန်:**\n\nကျေးဇူးပြု၍ သင်၏ Backup `.db` ဖိုင်ကို ဒီ Chat ထဲသို့ ပို့ပေးပါခင်ဗျာ။", parse_mode="Markdown")

@bot.message_handler(content_types=['document'])
def admin_handle_document(message):
    if message.from_user.id != ADMIN_ID: return
    # Restore ခလုတ်နှိပ်ထားလျှင် သို့မဟုတ် Caption တွင် /restore ပါလျှင်
    if waiting_for_restore.get(ADMIN_ID) or message.caption == "/restore":
        try:
            fi = bot.get_file(message.document.file_id)
            df = bot.download_file(fi.file_path)
            with open('vip_shop.db', 'wb') as f: f.write(df)
            waiting_for_restore[ADMIN_ID] = False
            bot.send_message(message.chat.id, "✅ **Database ကို အောင်မြင်စွာ Restore ပြုလုပ်ပြီးပါပြီခင်ဗျာ။**", parse_mode="Markdown")
        except Exception as e:
            bot.send_message(message.chat.id, "❌ Restore ပြုလုပ်ရာတွင် အမှားဖြစ်နေပါသည်: " + str(e))

@bot.message_handler(commands=['broadcast'])
def admin_broadcast(message):
    if message.from_user.id != ADMIN_ID: return
    txt = message.text.replace("/broadcast", "").strip()
    if not txt:
        bot.send_message(message.chat.id, "❌ ဥပမာ - `/broadcast မင်္ဂလာပါ`", parse_mode="Markdown")
        return
    with sqlite3.connect('vip_shop.db') as conn:
        users = conn.cursor().execute("SELECT user_id FROM users").fetchall()
    succ = 0
    for u in users:
        try:
            bot.send_message(u[0], txt)
            succ += 1
        except Exception: pass
    bot.send_message(message.chat.id, "✅ လူ " + str(succ) + " ဦးထံ ပို့ပြီးပါပြီ။")

@bot.message_handler(commands=['addnum'])
def admin_add_number(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        parts = message.text.replace("/addnum", "").strip().split(',')
        if len(parts) != 3:
            bot.send_message(message.chat.id, "❌ ဥပမာ - `/addnum 09 777 888 999, 150000, PRO`", parse_mode="Markdown")
            return
        phone = ''.join(filter(str.isdigit, parts[0]))
        price = float(parts[1].strip())
        ntype = parts[2].strip().upper()
        op = detect_operator(phone)
        with sqlite3.connect('vip_shop.db') as conn:
            conn.cursor().execute("INSERT INTO numbers (phone_number, operator, price, num_type) VALUES (?, ?, ?, ?)", (phone, op, price, ntype))
            conn.commit()
        bot.send_message(message.chat.id, "✅ ဖုန်းနံပါတ် " + phone + " (" + op + ") ထည့်ပြီးပါပြီ။")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Error: " + str(e))

# 📞 ဆိုင်နှင့် ဆက်သွယ်ရန်
@bot.message_handler(func=lambda m: m.text == "📞 ဆိုင်နှင့် ဆက်သွယ်ရန်")
def contact_shop(message):
    text = "📞 **Star Mobile VIP Shop**\n\n" + \
           "💬 Telegram Admin: @starmobile63956\n" + \
           "📱 ဖုန်းနံပါတ်: 09795096484 / 09792654163\n" + \
           "⏰ အလုပ်ချိန်: မနက် ၉ နာရီ မှ ည ၉ နာရီအထိ"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# 🛍️ USER SHOPPING LOGIC
@bot.message_handler(func=lambda m: m.text == "✨ နံပါတ်လှများကြည့်မည်")
@require_channel_join
def show_pro_numbers(message):
    send_paginated_numbers(message.chat.id, "PRO", 0)

@bot.message_handler(func=lambda m: m.text == "🍀 Lucky Phone ကြည့်မည်")
@require_channel_join
def show_lucky_numbers(message):
    send_paginated_numbers(message.chat.id, "LUCKY", 0)

def send_paginated_numbers(chat_id, n_type, page, is_edit=False, message_id=None):
    with sqlite3.connect('vip_shop.db') as conn:
        c = conn.cursor()
        tot = c.execute("SELECT COUNT(*) FROM numbers WHERE num_type=? AND status='AVAILABLE'", (n_type,)).fetchone()[0]
        if tot == 0:
            bot.send_message(chat_id, "📭 စာရင်း မရှိသေးပါ။")
            return
        tpages = math.ceil(tot / ITEMS_PER_PAGE)
        rows = c.execute("SELECT id, phone_number, operator, price FROM numbers WHERE num_type=? AND status='AVAILABLE' LIMIT ? OFFSET ?", (n_type, ITEMS_PER_PAGE, page * ITEMS_PER_PAGE)).fetchall()

    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        markup.add(types.InlineKeyboardButton(r[1] + " (" + r[2] + ") - " + "{:,.0f}".format(r[3]) + " ကျပ်", callback_data="buy_" + str(r[0])))

    nav = []
    if page > 0: nav.append(types.InlineKeyboardButton("⬅️ ရှေ့သို့", callback_data="page_" + n_type + "_" + str(page-1)))
    if page < tpages - 1: nav.append(types.InlineKeyboardButton("နောက်သို့ ➡️", callback_data="page_" + n_type + "_" + str(page+1)))
    if nav: markup.row(*nav)

    title = ("✨ နံပါတ်လှများ" if n_type == "PRO" else "🍀 Lucky Phone") + " (" + str(page+1) + "/" + str(tpages) + ")"
    if is_edit: bot.edit_message_text(title, chat_id, message_id, reply_markup=markup)
    else: bot.send_message(chat_id, title, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("page_"))
def handle_pagination(call):
    p = call.data.split("_")
    send_paginated_numbers(call.message.chat.id, p[1], int(p[2]), True, call.message.message_id)

@bot.message_handler(func=lambda m: m.text == "📡 Operator အလိုက်ကြည့်မည်")
@require_channel_join
def show_operators(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("MPT", callback_data="op_MPT"), types.InlineKeyboardButton("ATOM", callback_data="op_ATOM"),
               types.InlineKeyboardButton("Ooredoo", callback_data="op_Ooredoo"), types.InlineKeyboardButton("Mytel", callback_data="op_Mytel"))
    bot.send_message(message.chat.id, "Operator ရွေးပါ -", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("op_"))
def filter_by_operator(call):
    op = call.data.split("_")[1]
    with sqlite3.connect('vip_shop.db') as conn:
        rows = conn.cursor().execute("SELECT id, phone_number, price FROM numbers WHERE operator=? AND status='AVAILABLE'", (op,)).fetchall()
    if not rows:
        bot.answer_callback_query(call.id, "နံပါတ် မရှိပါ။")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        markup.add(types.InlineKeyboardButton(r[1] + " - " + "{:,.0f}".format(r[2]) + " ကျပ်", callback_data="buy_" + str(r[0])))
    bot.edit_message_text("📡 *" + op + "* နံပါတ်များ -", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def process_buy(call):
    nid = call.data.split("_")[1]
    with sqlite3.connect('vip_shop.db') as conn:
        item = conn.cursor().execute("SELECT phone_number, price, status FROM numbers WHERE id=?", (nid,)).fetchone()
    if not item or item[2] == 'SOLD':
        bot.answer_callback_query(call.id, "ဤနံပါတ် မရှိတော့ပါ။", show_alert=True)
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ မဝယ်တော့ပါ", callback_data="cancel_buy_" + str(nid)))
    txt = "🎯 နံပါတ်: " + str(item[0]) + "\n💰 ကျသင့်ငွေ: " + "{:,.0f}".format(item[1]) + " ကျပ်\n\n💳 Deli ခ 4,000 လွှဲရန်:\nKPay: 09795096484\nWave: 09792654163\n\n📝 နာမည်၊ ဖုန်း၊ လိပ်စာ အတိအကျ ရိုက်ထည့်ပေးပါ -"
    msg = bot.send_message(call.message.chat.id, txt, reply_markup=markup)
    bot.register_next_step_handler(msg, save_order, item[0], item[1], nid)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_buy_"))
def user_cancel_buy(call):
    bot.clear_step_handler_by_chat_id(call.message.chat.id)
    bot.send_message(call.message.chat.id, "ဝယ်ယူမှုကို ပယ်ဖျက်လိုက်ပါပြီ။", reply_markup=main_menu(call.from_user.id))

def save_order(message, phone, price, nid):
    if message.text in ["✨ နံပါတ်လှများကြည့်မည်", "🍀 Lucky Phone ကြည့်မည်", "📡 Operator အလိုက်ကြည့်မည်", "📞 ဆိုင်နှင့် ဆက်သွယ်ရန်", "👑 Admin Panel"]:
        bot.send_message(message.chat.id, "❌ ပယ်ဖျက်လိုက်ပါသည်။")
        return
    info = message.text
    uid = message.from_user.id
    fname = message.from_user.first_name
    with sqlite3.connect('vip_shop.db') as conn:
        c = conn.cursor()
        c.execute("UPDATE numbers SET status='SOLD' WHERE id=?", (nid,))
        c.execute("INSERT INTO orders (user_id, customer_name, chosen_number, price, contact_info, ref_id) VALUES (?, ?, ?, ?, ?, ?)", (uid, fname, phone, price, info, nid))
        conn.commit()
        oid = c.lastrowid
    bot.send_message(message.chat.id, "✅ အော်ဒါတင်ခြင်း အောင်မြင်ပါသည်။ (#ORD-" + "{:03d}".format(oid) + ")")
    try:
        bot.send_message(ADMIN_ID, "🔔 အော်ဒါသစ်: #ORD-" + "{:03d}".format(oid) + "\nဝယ်သူ: " + str(fname) + "\nဖုန်း: " + str(phone) + "\nဈေးနှုန်း: " + "{:,.0f}".format(price) + "\nလိပ်စာ: " + str(info))
    except Exception: pass

bot.polling(none_stop=True)
        
