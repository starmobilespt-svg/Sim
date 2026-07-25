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
ITEMS_PER_PAGE = 10

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
    markup.add("📡 Operator အလိုက်ကြည့်မည်", "🎮 Digital Acc များ") 
    markup.add("📞 ဆိုင်နှင့် ဆက်သွယ်ရန်")
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
           "📌 **ဖုန်းနံပါတ်အသစ်ထည့်ရန်:**\n" + \
           "`/addnum နံပါတ်, ဈေးနှုန်း, အမျိုးအစား`\n" + \
           "*(ဥပမာ: /addnum 09 777 888 999, 150000, PRO)*\n\n" + \
           "📌 **Digital Acc အသစ်ထည့်ရန်:**\n" + \
           "`/addacc အကောင့်အမည်, ဈေးနှုန်း, Platform`\n" + \
           "*(ဥပမာ: /addacc Netflix 1 Month, 15000, Netflix)*\n\n" + \
           "📌 **ပစ္စည်း အလွယ်ဖျက်ရန်:**\n" + \
           "`/del` ဟု ရိုက်ထည့်ပါ (သို့) အောက်ပါ ခလုတ်ကို နှိပ်ပါ။\n\n" + \
           "📌 **Broadcast စာပို့ရန်:**\n" + \
           "`/broadcast စာသား`"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📦 အော်ဒါများကြည့်ရန် / Cancel လုပ်ရန်", callback_data="admin_view_orders"),
        types.InlineKeyboardButton("📊 အရောင်းစာရင်း (Sales Report)", callback_data="admin_sales_report"),
        types.InlineKeyboardButton("🗑️ ရောင်းရန်ရှိသည့် ပစ္စည်းများဖျက်ရန်", callback_data="admin_del_list_0"),
        types.InlineKeyboardButton("💾 Database Backup ယူမည်", callback_data="admin_do_backup"),
        types.InlineKeyboardButton("🔄 Database Restore လုပ်မည်", callback_data="admin_start_restore")
    )
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

# 📊 ADMIN: အရောင်းစာရင်း ချုပ် (Sales Report)
@bot.callback_query_handler(func=lambda call: call.data == "admin_sales_report")
def admin_sales_report(call):
    if call.from_user.id != ADMIN_ID: return
    bot.answer_callback_query(call.id, "စာရင်း တွက်ချက်နေပါသည်...")
    
    with sqlite3.connect('vip_shop.db') as conn:
        c = conn.cursor()
        total_data = c.execute("SELECT SUM(price), COUNT(id) FROM orders WHERE status='COMPLETED'").fetchone()
        total_rev = total_data[0] if total_data[0] else 0
        total_orders = total_data[1] if total_data[1] else 0
        
        monthly_data = c.execute("SELECT strftime('%Y-%m', date) as month_year, COUNT(id), SUM(price) FROM orders WHERE status='COMPLETED' GROUP BY month_year ORDER BY month_year DESC").fetchall()
        
    text = "📊 **အရောင်းစာရင်း ချုပ် (Sales Report)**\n"
    text += "────────────────────\n"
    text += f"🏆 **စုစုပေါင်း ရောင်းရငွေ:** {total_rev:,.0f} ကျပ်\n"
    text += f"📦 **စုစုပေါင်း ရောင်းရအရေအတွက်:** {total_orders} ခု\n"
    text += "────────────────────\n\n"
    text += "📅 **လအလိုက် ရောင်းရငွေများ:**\n"
    
    if not monthly_data:
        text += "မှတ်တမ်း မရှိသေးပါ။"
    else:
        for r in monthly_data:
            month_str = r[0]   
            count = r[1]       
            m_total = r[2] if r[2] else 0
            text += f"🔹 **{month_str}** : {m_total:,.0f} ကျပ် ({count} ခု)\n"
            
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

# 👑 ADMIN: အော်ဒါများကြည့်ရန်၊ ပြီးစီးကြောင်း မှတ်ရန် နှင့် Cancel လုပ်ရန်
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
        phone_txt = str(r[2])
        txt = "📦 **အော်ဒါနံပါတ်:** #ORD-" + "{:03d}".format(r[0]) + "\n" + \
              "👤 **ဝယ်သူ:** " + str(r[1]) + " (ID: `" + str(r[5]) + "`)\n" + \
              "🛍 **မှာယူသည့်အရာ:** `" + phone_txt + "`\n" + \
              "💰 **ကျသင့်ငွေ:** " + "{:,.0f}".format(r[3]) + " ကျပ်\n" + \
              "📍 **လိပ်စာ/အချက်အလက်:** " + str(r[4])
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("✅ ပြီးစီးပါပြီ (Completed)", callback_data="admin_comp_ord_" + str(r[0])),
            types.InlineKeyboardButton("❌ ဤအော်ဒါကို Cancel မည်", callback_data="admin_cancel_ord_" + str(r[0]))
        )
        bot.send_message(call.message.chat.id, txt, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_comp_ord_"))
def admin_complete_order(call):
    if call.from_user.id != ADMIN_ID: return
    oid = int(call.data.split("_")[3])
    
    with sqlite3.connect('vip_shop.db') as conn:
        c = conn.cursor()
        ord_data = c.execute("SELECT user_id, chosen_number FROM orders WHERE id=?", (oid,)).fetchone()
        
        if ord_data:
            user_id, phone = ord_data
            c.execute("UPDATE orders SET status='COMPLETED' WHERE id=?", (oid,))
            conn.commit()
            
            phone_txt = str(phone)
            bot.answer_callback_query(call.id, "အော်ဒါ ပြီးစီးကြောင်း မှတ်သားလိုက်ပါပြီ။", show_alert=True)
            bot.edit_message_text("✅ **အော်ဒါ #ORD-" + "{:03d}".format(oid) + " ကို အောင်မြင်စွာ ပို့ဆောင်ပြီးပါပြီ။**", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            
            try:
                msg = "🎉 **ဝမ်းသာစရာ သတင်းပါခင်ဗျာ!**\n\nလူကြီးမင်း၏ အော်ဒါ #ORD-" + "{:03d}".format(oid) + " (`" + phone_txt + "`) ကို ဆိုင်မှ အောင်မြင်စွာ ပို့ဆောင်ပေးလိုက်ပါပြီ။\n\nအားပေးမှုကို အထူးကျေးဇူးတင်ရှိပါသည်။ 🙏"
                bot.send_message(user_id, msg, parse_mode="Markdown")
            except Exception: 
                pass

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
            
            phone_txt = str(phone)
            bot.answer_callback_query(call.id, "အော်ဒါကို ပယ်ဖျက်လိုက်ပါပြီ။", show_alert=True)
            bot.edit_message_text("❌ **အော်ဒါ #ORD-" + "{:03d}".format(oid) + " ကို Admin မှ Cancel လိုက်ပါသည်။**", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            
            try:
                bot.send_message(user_id, "ℹ️ သင်၏ အော်ဒါ #ORD-" + "{:03d}".format(oid) + " (`" + phone_txt + "`) ကို Admin မှ ပယ်ဖျက်လိုက်ပါပြီ။")
            except Exception: pass

# 📌 ဖျက်ရန် စာရင်းကို လွယ်ကူစွာ ပြပေးမည့် Function 
def show_delete_list(chat_id, page, is_edit=False, message_id=None):
    with sqlite3.connect('vip_shop.db') as conn:
        c = conn.cursor()
        tot = c.execute("SELECT COUNT(*) FROM numbers WHERE status='AVAILABLE'").fetchone()[0]
        if tot == 0:
            if is_edit: bot.edit_message_text("📭 ရောင်းရန် ပစ္စည်း မရှိသေးပါ။", chat_id, message_id)
            else: bot.send_message(chat_id, "📭 ရောင်းရန် ပစ္စည်း မရှိသေးပါ။")
            return
            
        tpages = math.ceil(tot / ITEMS_PER_PAGE)
        if page >= tpages: page = tpages - 1
        if page < 0: page = 0
            
        rows = c.execute("SELECT id, phone_number, price, num_type FROM numbers WHERE status='AVAILABLE' ORDER BY id DESC LIMIT ? OFFSET ?", (ITEMS_PER_PAGE, page * ITEMS_PER_PAGE)).fetchall()
        
    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        item_name = str(r[1])
        price_str = "{:,.0f}".format(r[2])
        ntype = str(r[3])
        btn_txt = f"🗑 {item_name} ({price_str} Ks) [{ntype}]"
        markup.add(types.InlineKeyboardButton(btn_txt, callback_data=f"admin_del_item_{r[0]}_{page}"))
        
    nav = []
    if page > 0: nav.append(types.InlineKeyboardButton("⬅️ ရှေ့သို့", callback_data=f"admin_del_list_{page-1}"))
    if page < tpages - 1: nav.append(types.InlineKeyboardButton("နောက်သို့ ➡️", callback_data=f"admin_del_list_{page+1}"))
    if nav: markup.row(*nav)
    
    title = f"🗑️ **ပစ္စည်းများ ဖျက်ရန်** ({page+1}/{tpages})\n\n*(ဖျက်လိုသော ပစ္စည်းကို နှိပ်ပါ၊ စာရင်းမှာ ချက်ချင်း Refresh ဖြစ်သွားပါမည်)*"
    try:
        if is_edit:
            bot.edit_message_text(title, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, title, reply_markup=markup, parse_mode="Markdown")
    except Exception: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_del_list_"))
def admin_delete_list_paginated(call):
    if call.from_user.id != ADMIN_ID: return
    page = int(call.data.split("_")[3])
    show_delete_list(call.message.chat.id, page, is_edit=True, message_id=call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_del_item_"))
def admin_delete_item_action(call):
    if call.from_user.id != ADMIN_ID: return
    parts = call.data.split("_")
    nid = int(parts[3])
    page = int(parts[4])
    
    with sqlite3.connect('vip_shop.db') as conn:
        c = conn.cursor()
        num = c.execute("SELECT phone_number FROM numbers WHERE id=?", (nid,)).fetchone()
        if num:
            c.execute("DELETE FROM numbers WHERE id=?", (nid,))
            conn.commit()
            bot.answer_callback_query(call.id, f"✅ '{num[0]}' ကို ဖျက်လိုက်ပါပြီ။", show_alert=False)
            show_delete_list(call.message.chat.id, page, is_edit=True, message_id=call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "ပစ္စည်း မတွေ့ရှိပါ။", show_alert=True)

# 👑 ADMIN: /del Command ဖြင့် ပစ္စည်းဖျက်ရန်
@bot.message_handler(commands=['del'])
def admin_delete_by_name(message):
    if message.from_user.id != ADMIN_ID: return
    item_name = message.text.replace("/del", "").strip()
    
    if not item_name:
        show_delete_list(message.chat.id, 0, is_edit=False)
        return
        
    with sqlite3.connect('vip_shop.db') as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM numbers WHERE phone_number=? AND status='AVAILABLE'", (item_name,))
        rows = c.fetchall()
        if not rows:
            bot.send_message(message.chat.id, f"❌ ရောင်းရန်စာရင်းထဲတွင် '{item_name}' ကို မတွေ့ပါ။\n(ရှာမတွေ့ပါက `/del` ဟုသာ ရိုက်ထည့်၍ ခလုတ်များဖြင့် ရှာဖွေနိုင်ပါသည်)")
            return
        c.execute("DELETE FROM numbers WHERE phone_number=? AND status='AVAILABLE'", (item_name,))
        conn.commit()
    bot.send_message(message.chat.id, f"✅ '{item_name}' (စုစုပေါင်း {len(rows)} ခု) ကို အောင်မြင်စွာ ဖျက်လိုက်ပါပြီ။")

# 👑 ADMIN: DATABASE BACKUP & RESTORE
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
        
        phone = parts[0].strip()
        price = float(parts[1].strip())
        ntype = parts[2].strip().upper()
        op = detect_operator(phone)
        with sqlite3.connect('vip_shop.db') as conn:
            conn.cursor().execute("INSERT INTO numbers (phone_number, operator, price, num_type) VALUES (?, ?, ?, ?)", (phone, op, price, ntype))
            conn.commit()
        bot.send_message(message.chat.id, "✅ ဖုန်းနံပါတ် " + phone + " (" + op + ") ထည့်ပြီးပါပြီ။")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Error: " + str(e))

# 📌 DIGITAL ACC အသစ်ထည့်ရန် Command
@bot.message_handler(commands=['addacc'])
def admin_add_acc(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        parts = message.text.replace("/addacc", "").strip().split(',')
        if len(parts) != 3:
            bot.send_message(message.chat.id, "❌ ဥပမာ - `/addacc Netflix 1 Month, 15000, Netflix`", parse_mode="Markdown")
            return
        
        acc_name = parts[0].strip()
        price = float(parts[1].strip())
        platform = parts[2].strip()
        ntype = "DIGITAL"
        
        with sqlite3.connect('vip_shop.db') as conn:
            conn.cursor().execute("INSERT INTO numbers (phone_number, operator, price, num_type) VALUES (?, ?, ?, ?)", (acc_name, platform, price, ntype))
            conn.commit()
        bot.send_message(message.chat.id, f"✅ Digital Acc '{acc_name}' ထည့်ပြီးပါပြီ။")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Error: " + str(e))

# 📞 ဆိုင်နှင့် ဆက်သွယ်ရန်
@bot.message_handler(func=lambda m: m.text == "📞 ဆိုင်နှင့် ဆက်သွယ်ရန်")
def contact_shop(message):
    text = "📞 **Star Mobile VIP Shop**\n\n" + \
           "💬 Telegram Admin: @starmobile63956\n" + \
           "📱 ဖုန်းနံပါတ်: 09 7950 96484 / 09 7926 54163\n" + \
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

# 📌 Digital Acc များ ကြည့်ရန်
@bot.message_handler(func=lambda m: m.text == "🎮 Digital Acc များ")
@require_channel_join
def show_digital_accs(message):
    send_paginated_numbers(message.chat.id, "DIGITAL", 0)

def send_paginated_numbers(chat_id, n_type, page, is_edit=False, message_id=None):
    with sqlite3.connect('vip_shop.db') as conn:
        c = conn.cursor()
        tot = c.execute("SELECT COUNT(*) FROM numbers WHERE num_type=? AND status='AVAILABLE'", (n_type,)).fetchone()[0]
        if tot == 0:
            if is_edit: bot.edit_message_text("📭 စာရင်း မရှိသေးပါ။", chat_id, message_id)
            else: bot.send_message(chat_id, "📭 စာရင်း မရှိသေးပါ။")
            return
        tpages = math.ceil(tot / ITEMS_PER_PAGE)
        rows = c.execute("SELECT id, phone_number, operator, price FROM numbers WHERE num_type=? AND status='AVAILABLE' ORDER BY price ASC LIMIT ? OFFSET ?", (n_type, ITEMS_PER_PAGE, page * ITEMS_PER_PAGE)).fetchall()

    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        phone_txt = str(r[1])
        markup.add(types.InlineKeyboardButton(phone_txt + " (" + r[2] + ") - " + "{:,.0f}".format(r[3]) + " ကျပ်", callback_data="buy_" + str(r[0])))

    nav = []
    if page > 0: nav.append(types.InlineKeyboardButton("⬅️ ရှေ့သို့", callback_data="page_" + n_type + "_" + str(page-1)))
    if page < tpages - 1: nav.append(types.InlineKeyboardButton("နောက်သို့ ➡️", callback_data="page_" + n_type + "_" + str(page+1)))
    if nav: markup.row(*nav)

    if n_type == "PRO": title_prefix = "✨ နံပါတ်လှများ"
    elif n_type == "LUCKY": title_prefix = "🍀 Lucky Phone"
    elif n_type == "DIGITAL": title_prefix = "🎮 Digital Accounts"
    else: title_prefix = "📦 ပစ္စည်းများ"
    
    title = f"{title_prefix} ({page+1}/{tpages})"
    
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

def send_paginated_operators(chat_id, op, page, is_edit=False, message_id=None):
    with sqlite3.connect('vip_shop.db') as conn:
        c = conn.cursor()
        tot = c.execute("SELECT COUNT(*) FROM numbers WHERE operator=? AND status='AVAILABLE'", (op,)).fetchone()[0]
        if tot == 0:
            if is_edit: bot.edit_message_text("📭 စာရင်း မရှိသေးပါ။", chat_id, message_id)
            else: bot.send_message(chat_id, "📭 စာရင်း မရှိသေးပါ။")
            return
            
        tpages = math.ceil(tot / ITEMS_PER_PAGE)
        rows = c.execute("SELECT id, phone_number, price FROM numbers WHERE operator=? AND status='AVAILABLE' ORDER BY price ASC LIMIT ? OFFSET ?", (op, ITEMS_PER_PAGE, page * ITEMS_PER_PAGE)).fetchall()

    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        phone_txt = str(r[1])
        markup.add(types.InlineKeyboardButton(phone_txt + " - " + "{:,.0f}".format(r[2]) + " ကျပ်", callback_data="buy_" + str(r[0])))

    nav = []
    if page > 0: nav.append(types.InlineKeyboardButton("⬅️ ရှေ့သို့", callback_data="oppage_" + op + "_" + str(page-1)))
    if page < tpages - 1: nav.append(types.InlineKeyboardButton("နောက်သို့ ➡️", callback_data="oppage_" + op + "_" + str(page+1)))
    if nav: markup.row(*nav)

    title = "📡 *" + op + "* နံပါတ်များ (" + str(page+1) + "/" + str(tpages) + ")"
    if is_edit: 
        bot.edit_message_text(title, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
    else: 
        bot.send_message(chat_id, title, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("op_"))
def filter_by_operator(call):
    op = call.data.split("_")[1]
    send_paginated_operators(call.message.chat.id, op, 0, True, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("oppage_"))
def handle_op_pagination(call):
    p = call.data.split("_")
    send_paginated_operators(call.message.chat.id, p[1], int(p[2]), True, call.message.message_id)

# 📌 ပစ္စည်းဝယ်ယူသည့် အပိုင်း (Digital Acc နှင့် ရိုးရိုးပစ္စည်း ခွဲခြားထားသည်)
@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def process_buy(call):
    nid = call.data.split("_")[1]
    with sqlite3.connect('vip_shop.db') as conn:
        item = conn.cursor().execute("SELECT phone_number, price, status, num_type FROM numbers WHERE id=?", (nid,)).fetchone()
    
    # ရိုးရိုးပစ္စည်း (ဖုန်းနံပါတ်များ) အတွက် SOLD ဖြစ်နေလျှင် မရနိုင်ကြောင်း ပြမည်
    if not item or (item[2] == 'SOLD' and item[3] != 'DIGITAL'):
        bot.answer_callback_query(call.id, "ဤပစ္စည်း မရှိတော့ပါ။", show_alert=True)
        return
    
    phone_txt = str(item[0])
    price = item[1]
    ntype = str(item[3])
    
    markup = types.InlineKeyboardMarkup()
    
    # 📌 DIGITAL ACCOUNT ဝယ်ယူခြင်းဖြစ်ပါက
    if ntype == "DIGITAL":
        markup.add(
            types.InlineKeyboardButton("✅ သေချာပါသည် ဝယ်ယူမည်", callback_data="confdigi_" + str(nid)),
            types.InlineKeyboardButton("❌ မဝယ်တော့ပါ", callback_data="cancel_buy_" + str(nid))
        )
        txt = f"🎮 **ရွေးချယ်ထားသော အကောင့်:** {phone_txt}\n💰 **ကျသင့်ငွေ:** {price:,.0f} ကျပ်\n\n⚠️ ဤအကောင့်ကို ဝယ်ယူရန် သေချာပါသလား?"
        bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        
    # 📌 ရိုးရိုးဖုန်းနံပါတ် ဝယ်ယူခြင်းဖြစ်ပါက (Delivery ခ ပါမည်)
    else:
        markup.add(types.InlineKeyboardButton("❌ မဝယ်တော့ပါ", callback_data="cancel_buy_" + str(nid)))
        txt = f"🎯 ရွေးချယ်ထားသောပစ္စည်း: {phone_txt}\n💰 ဈေးနှုန်း: {price:,.0f} ကျပ်\n\n💳 Deli ခ 4,000 လွှဲရန်:\nKPay: 09 7950 96484\nWave: 09 7926 54163\n\n📝 နာမည်၊ ဖုန်း၊ လိပ်စာ အတိအကျ ရိုက်ထည့်ပေးပါ -"
        msg = bot.send_message(call.message.chat.id, txt, reply_markup=markup)
        bot.register_next_step_handler(msg, save_order, phone_txt, price, nid)

# 📌 DIGITAL ACC သေချာကြောင်း နှိပ်လိုက်သောအခါ
@bot.callback_query_handler(func=lambda call: call.data.startswith("confdigi_"))
def confirm_digital_buy(call):
    nid = call.data.split("_")[1]
    uid = call.from_user.id
    fname = call.from_user.first_name
    
    with sqlite3.connect('vip_shop.db') as conn:
        item = conn.cursor().execute("SELECT phone_number, price FROM numbers WHERE id=?", (nid,)).fetchone()
        if not item: return
        phone = item[0]
        price = item[1]
        
        c = conn.cursor()
        # 📌 DIGITAL ACC ဖြစ်သောကြောင့် UPDATE numbers SET status='SOLD' ကို မလုပ်ပါ။ (အမြဲတမ်း ဆက်ပြထားမည်)
        c.execute("INSERT INTO orders (user_id, customer_name, chosen_number, price, contact_info, ref_id) VALUES (?, ?, ?, ?, ?, ?)", (uid, fname, phone, price, "Digital Account (Telegram မှ ဆက်သွယ်မည်)", nid))
        conn.commit()
        oid = c.lastrowid
        
    bot.answer_callback_query(call.id, "ဝယ်ယူရန် ရွေးချယ်မှု အောင်မြင်ပါသည်။")
    
    txt = f"✅ **အော်ဒါ ရွေးချယ်မှု အောင်မြင်ပါသည်။** (#ORD-{oid:03d})\n\n"
    txt += f"🎮 **အကောင့်:** {phone}\n💰 **ကျသင့်ငွေ:** {price:,.0f} ကျပ်\n\n"
    txt += "💬 **ငွေပေးချေရန်နှင့် အကောင့်ရယူရန်အတွက် -**\nကျေးဇူးပြု၍ Admin 👉 @starmobile63956 သို့ ယခုပဲ Message သွားပို့ပေးပါခင်ဗျာ။"
    
    bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    
    # 📌 Admin ထံ Notification ပို့ခြင်း
    try:
        bot.send_message(ADMIN_ID, f"🔔 **Digital အော်ဒါသစ်:** #ORD-{oid:03d}\n👤 ဝယ်သူ: {fname}\n🛍 အကောင့်: {phone}\n💰 ဈေးနှုန်း: {price:,.0f} ကျပ်\n(ဝယ်သူမှ Telegram တွင် လာရောက်ဆက်သွယ်ပါမည်။)", parse_mode="Markdown")
    except Exception: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_buy_"))
def user_cancel_buy(call):
    bot.clear_step_handler_by_chat_id(call.message.chat.id)
    bot.send_message(call.message.chat.id, "ဝယ်ယူမှုကို ပယ်ဖျက်လိုက်ပါပြီ။", reply_markup=main_menu(call.from_user.id))

# 📌 ရိုးရိုးဖုန်းနံပါတ် အော်ဒါသိမ်းဆည်းခြင်း
def save_order(message, phone, price, nid):
    if message.text in ["✨ နံပါတ်လှများကြည့်မည်", "🍀 Lucky Phone ကြည့်မည်", "📡 Operator အလိုက်ကြည့်မည်", "🎮 Digital Acc များ", "📞 ဆိုင်နှင့် ဆက်သွယ်ရန်", "👑 Admin Panel"]:
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
        phone_txt = str(phone)
        bot.send_message(ADMIN_ID, "🔔 အော်ဒါသစ်: #ORD-" + "{:03d}".format(oid) + "\nဝယ်သူ: " + str(fname) + "\nမှာယူသည့်အရာ: " + phone_txt + "\nဈေးနှုန်း: " + "{:,.0f}".format(price) + "\nလိပ်စာ: " + str(info))
    except Exception:
        pass

# 🚀 Bot စတင် Run ရန်
print("Bot is running...")
if __name__ == "__main__":
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)
