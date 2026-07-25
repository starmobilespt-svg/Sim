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

admin_states = {}
user_topup_amounts = {}
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
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, phone_number TEXT, operator TEXT, price REAL, num_type TEXT, status TEXT DEFAULT 'AVAILABLE', digital_info TEXT DEFAULT '')''')
        c.execute('''CREATE TABLE IF NOT EXISTS orders 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, customer_name TEXT, chosen_number TEXT, price REAL, contact_info TEXT, ref_id INTEGER, status TEXT DEFAULT 'PENDING', date TIMESTAMP DEFAULT (datetime('now', 'localtime')))''')
        c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_name TEXT, balance REAL DEFAULT 0)''')
        conn.commit()

init_db()

def register_user(user_id, first_name):
    with sqlite3.connect('vip_shop.db') as conn:
        conn.cursor().execute("INSERT OR IGNORE INTO users (user_id, first_name, balance) VALUES (?, ?, 0)", (user_id, first_name))
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
    markup.add("👛 မိမိအကောင့်", "📞 ဆိုင်နှင့် ဆက်သွယ်ရန်")
    if user_id == ADMIN_ID: markup.add("👑 Admin Panel")
    return markup

def not_joined_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📢 Channel သို့သွားရန်", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"),
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

# 👛 မိမိအကောင့် (Wallet)
@bot.message_handler(func=lambda m: m.text == "👛 မိမိအကောင့်")
@require_channel_join
def show_wallet(message):
    uid = message.from_user.id
    with sqlite3.connect('vip_shop.db') as conn:
        res = conn.cursor().execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
        balance = res[0] if res else 0
        
    text = f"👛 **သင်၏ အကောင့်အချက်အလက်**\n\n💰 လက်ကျန် Point: `{balance:,.0f}` ကျပ်"
           
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💳 point ထည့်မည်", callback_data="user_start_topup"))
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "user_start_topup")
def user_start_topup(call):
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("500", callback_data="topup_amt_500"),
        types.InlineKeyboardButton("1000", callback_data="topup_amt_1000"),
        types.InlineKeyboardButton("3000", callback_data="topup_amt_3000")
    )
    markup.add(types.InlineKeyboardButton("✍️ ကိုယ်တိုင် ပမာဏရိုက်ထည့်မည်", callback_data="topup_custom_input"))
    txt = "💳 **ထည့်သွင်းမည့် Point ပမာဏကို ရွေးချယ်ပါ** (သို့မဟုတ်) အောက်ပါခလုတ်ကို နှိပ်၍ လိုသလောက် ရိုက်ထည့်နိုင်ပါသည်:"
    
    try:
        bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    except Exception:
        bot.send_message(call.message.chat.id, txt, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "topup_custom_input")
def topup_custom_input(call):
    admin_states[call.from_user.id] = {"action": "waiting_user_custom_topup"}
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "✍️ ကျေးဇူးပြု၍ ထည့်သွင်းလိုသော ပမာဏကို ရိုက်ထည့်ပေးပါ:\n*(ရာပိတ် / ရာဂဏန်းသာ ဖြစ်ရပါမည်။ ဥပမာ - 1100, 1500)*", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("topup_amt_"))
def topup_preset_amount(call):
    amount = float(call.data.split("_")[2])
    uid = call.from_user.id
    user_topup_amounts[uid] = amount
    show_payment_gateways(call.message.chat.id, call.message.message_id, amount)

def show_payment_gateways(chat_id, message_id, amount):
    txt = f"💳 **ရွေးချယ်ထားသော ပမာဏ:** `{amount:,.0f}` ကျပ်\n\n" \
          f"အောက်ပါ အကောင့်များသို့ ငွေလွှဲပြီး ငွေလွှဲပြေစာ (Screenshot) ကို ပို့ပေးပါ။\n\n" \
          f"Wave: `09 792 654 163` (Si Thu Aung)\n" \
          f"Kpay: `09 79 50 96 484` (Si Thu Aung)"
          
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📤 ငွေလွှဲပြေစာ (SS) ပို့မည်", callback_data="user_send_topup_ss"))
    
    try:
        bot.edit_message_text(txt, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
    except Exception:
        bot.send_message(chat_id, txt, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in admin_states and admin_states[m.from_user.id].get("action") == "waiting_user_custom_topup")
def receive_custom_topup_amount(message):
    uid = message.from_user.id
    try:
        amount = float(message.text.strip())
        
        if amount % 100 != 0:
            bot.send_message(message.chat.id, "⚠️ **ရာဂဏန်း (ရာပိတ်) သာ လက်ခံပါသည်။** ဥပမာ: `1100`, `1500` ကဲ့သို့သော ပမာဏကိုသာ ရိုက်ထည့်ပါ။ ကျေးဇူးပြု၍ ထပ်မံကြိုးစားပါ:", parse_mode="Markdown")
            return
            
        del admin_states[uid]
        user_topup_amounts[uid] = amount
        
        txt = f"💳 **ရွေးချယ်ထားသော ပမာဏ:** `{amount:,.0f}` ကျပ်\n\n" \
              f"အောက်ပါ အကောင့်များသို့ ငွေလွှဲပြီး ငွေလွှဲပြေစာ (Screenshot) ကို ပို့ပေးပါ။\n\n" \
              f"Wave: `09 792 654 163` (Si Thu Aung)\n" \
              f"Kpay: `09 79 50 96 484` (Si Thu Aung)"
              
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📤 ငွေလွှဲပြေစာ (SS) ပို့မည်", callback_data="user_send_topup_ss"))
        bot.send_message(message.chat.id, txt, reply_markup=markup, parse_mode="Markdown")
    except ValueError:
        bot.send_message(message.chat.id, "❌ နံပါတ်သာ မှန်ကန်စွာ ရိုက်ထည့်ပါ။")

@bot.callback_query_handler(func=lambda call: call.data == "user_send_topup_ss")
def user_topup_ss_prompt(call):
    msg = bot.send_message(call.message.chat.id, "🖼️ ကျေးဇူးပြု၍ ငွေလွှဲထားသော **Screenshot (SS) ပုံ** ကို ပို့ပေးပါ။")
    bot.register_next_step_handler(msg, receive_topup_ss)

def receive_topup_ss(message):
    if message.content_type != 'photo':
        bot.send_message(message.chat.id, "❌ ကျေးဇူးပြု၍ ပုံ (Photo) သာ ပို့ပေးပါ။")
        return
        
    photo_id = message.photo[-1].file_id
    uid = message.from_user.id
    fname = message.from_user.first_name
    amount = user_topup_amounts.get(uid, 0)
    
    user_link = f"[{fname}](tg://user?id={uid})"
    admin_txt = f"💳 **ငွေဖြည့်ရန် ငွေလွှဲပြေစာ (SS) ရောက်ရှိလာပါပြီ**\n\n👤 ဝယ်သူ: {user_link}\n🆔 User ID: `{uid}`\n💰 ရွေးချယ်ထားသော ပမာဏ: `{amount:,.0f}` ကျပ်"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ ခွင့်ပြုသည်", callback_data=f"admin_approve_topup_{uid}"))
    
    try:
        bot.send_photo(ADMIN_ID, photo_id, caption=admin_txt, reply_markup=markup, parse_mode="Markdown")
        bot.send_message(message.chat.id, "✅ ငွေလွှဲပြေစာ ပို့ခြင်း အောင်မြင်ပါသည်။ Admin မှ စစ်ဆေးအတည်ပြုပေးပါလိမ့်မည်။")
    except Exception:
        bot.send_message(message.chat.id, "❌ ပို့ဆောင်ရာတွင် အမှားဖြစ်နေပါသည်၊ ထပ်မံကြိုးစားပါ။")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_approve_topup_"))
def admin_approve_topup(call):
    if call.from_user.id != ADMIN_ID: return
    target_uid = int(call.data.split("_")[3])
    
    admin_states[ADMIN_ID] = {"action": "waiting_topup_amount", "target_uid": target_uid}
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, f"📥 ဤ User (`{target_uid}`) ထံသို့ ထည့်သွင်းပေးမည့် Point ပမာဏကို ရိုက်ထည့်ပေးပါ (ဥပမာ - `1500`):\n*(ရာပိတ် / ရာဂဏန်းသာ ဖြစ်ရပါမည်)*", parse_mode="Markdown")

# 👑 ADMIN PANEL & CONTROL BUTTONS
@bot.message_handler(func=lambda m: m.text == "👑 Admin Panel")
def show_admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    text = "👑 **Admin Control Panel**\n\n" + \
           "📌 **ဖုန်းနံပါတ်အသစ်ထည့်ရန်:** `/addnum နံပါတ်, ဈေးနှုန်း, အမျိုးအစား`\n" + \
           "📌 **Digital Acc အသစ်ထည့်ရန်:** `/addacc အမည်, ဈေးနှုန်း, Platform, AUTO/MANUAL, အချက်အလက်`\n" + \
           "📌 **Point ထည့်ပေးရန် (Command):** `/addbal user_id, 1000`\n" + \
           "📌 **Point နှုတ်ရန် (ပိုသွားပါက):** `/subbal user_id, 500`\n" + \
           "📌 **ပစ္စည်းဖျက်ရန်:** `/del` | **အော်ဒါ Cancel ရန်:** `/cancel အော်ဒါနံပါတ်`"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📦 PENDING အော်ဒါဟောင်းများ ကြည့်ရန်", callback_data="admin_view_orders"),
        types.InlineKeyboardButton("📊 အရောင်းစာရင်း (Sales Report)", callback_data="admin_sales_report"),
        types.InlineKeyboardButton("🗑️ ရောင်းရန်ရှိသည့် ပစ္စည်းများဖျက်ရန်", callback_data="admin_del_list_0"),
        types.InlineKeyboardButton("💾 Database Backup ယူမည်", callback_data="admin_do_backup"),
        types.InlineKeyboardButton("🔄 Database Restore လုပ်မည်", callback_data="admin_start_restore")
    )
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=['addbal'])
def admin_add_balance(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        parts = message.text.replace("/addbal", "").strip().split(',')
        if len(parts) != 2:
            bot.send_message(message.chat.id, "❌ ပုံစံမှားနေပါသည်။ ဥပမာ - `/addbal 8668319365, 1000`", parse_mode="Markdown")
            return
        
        target_uid = int(parts[0].strip())
        amount = float(parts[1].strip())
        
        if amount % 100 != 0:
            bot.send_message(message.chat.id, "⚠️ ရာဂဏန်း (ရာပိတ်) သာ လက်ခံပါသည်။")
            return
            
        with sqlite3.connect('vip_shop.db') as conn:
            c = conn.cursor()
            user = c.execute("SELECT balance FROM users WHERE user_id=?", (target_uid,)).fetchone()
            if not user:
                bot.send_message(message.chat.id, "❌ ဤ User ID ကို မတွေ့ပါ။")
                return
            
            new_bal = user[0] + amount
            c.execute("UPDATE users SET balance = ? WHERE user_id=?", (new_bal, target_uid))
            conn.commit()
            
        bot.send_message(message.chat.id, f"✅ User ID `{target_uid}` သို့ **{amount:,.0f}** ကျပ် ထည့်သွင်းပြီးပါပြီ။ (လက်ကျန်ငွေ: {new_bal:,.0f} ကျပ်)", parse_mode="Markdown")
        try:
            bot.send_message(target_uid, f"🎉 **ငွေလက်ခံရရှိပါပြီ!**\n\nသင်၏ အကောင့်ထဲသို့ Admin မှ ပမာဏ **{amount:,.0f}** ကျပ် ထည့်သွင်းပေးလိုက်ပါပြီ။\n💰 လက်ကျန်ငွေစုစုပေါင်း: `{new_bal:,.0f}` ကျပ်", parse_mode="Markdown")
        except Exception: pass
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Error: " + str(e))

@bot.message_handler(commands=['subbal'])
def admin_sub_balance(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        parts = message.text.replace("/subbal", "").strip().split(',')
        if len(parts) != 2:
            bot.send_message(message.chat.id, "❌ ပုံစံမှားနေပါသည်။ ဥပမာ - `/subbal 8668319365, 500`", parse_mode="Markdown")
            return
        
        target_uid = int(parts[0].strip())
        amount = float(parts[1].strip())
        
        if amount % 100 != 0:
            bot.send_message(message.chat.id, "⚠️ ရာဂဏန်း (ရာပိတ်) သာ လက်ခံပါသည်။")
            return
            
        with sqlite3.connect('vip_shop.db') as conn:
            c = conn.cursor()
            user = c.execute("SELECT balance FROM users WHERE user_id=?", (target_uid,)).fetchone()
            if not user:
                bot.send_message(message.chat.id, "❌ ဤ User ID ကို မတွေ့ပါ။")
                return
            
            new_bal = max(0, user[0] - amount)
            c.execute("UPDATE users SET balance = ? WHERE user_id=?", (new_bal, target_uid))
            conn.commit()
            
        bot.send_message(message.chat.id, f"✅ User ID `{target_uid}` ထံမှ **{amount:,.0f}** ကျပ် နှုတ်ယူလိုက်ပါပြီ။ (လက်ကျန်ငွေ: {new_bal:,.0f} ကျပ်)", parse_mode="Markdown")
        try:
            bot.send_message(target_uid, f"⚠️ **အကောင့်လက်ကျန် ဖြတ်တောက်ခံရမှု!**\n\nသင်၏ အကောင့်ထဲမှ Admin မှ **{amount:,.0f}** ကျပ် နှုတ်ယူလိုက်ပါပြီ။\n💰 လက်ကျန်ငွေစုစုပေါင်း: `{new_bal:,.0f}` ကျပ်", parse_mode="Markdown")
        except Exception: pass
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Error: " + str(e))

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and ADMIN_ID in admin_states)
def admin_handle_state_input(message):
    state = admin_states[ADMIN_ID]
    if state.get("action") == "waiting_topup_amount":
        try:
            amount = float(message.text.strip())
            
            if amount % 100 != 0:
                bot.send_message(message.chat.id, "⚠️ **ရာဂဏန်း (ရာပိတ်) သာ လက်ခံပါသည်။** ကျေးဇူးပြု၍ ပမာဏအမှန်ကို ထပ်မံရိုက်ထည့်ပါ:", parse_mode="Markdown")
                return
                
            target_uid = state["target_uid"]
            
            with sqlite3.connect('vip_shop.db') as conn:
                c = conn.cursor()
                c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, target_uid))
                conn.commit()
                res = c.execute("SELECT balance FROM users WHERE user_id=?", (target_uid,)).fetchone()
                new_bal = res[0] if res else amount
                
            del admin_states[ADMIN_ID]
            
            bot.send_message(message.chat.id, f"✅ User (`{target_uid}`) အကောင့်ထဲသို့ **{amount:,.0f}** ကျပ် အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ။\n💰 သူ၏လက်ကျန်ငွေ: `{new_bal:,.0f}` ကျပ်", parse_mode="Markdown")
            
            try:
                msg = f"🎉 **ငွေဖြည့်သွင်းမှု အောင်မြင်ပါသည်!**\n\nAdmin မှ သင့်အကောင့်ထဲသို့ ပမာဏ **{amount:,.0f}** ကျပ် ထည့်သွင်းပေးလိုက်ပါပြီ။\n💰 လက်ကျန်ငွေစုစုပေါင်း: `{new_bal:,.0f}` ကျပ်"
                bot.send_message(target_uid, msg, parse_mode="Markdown")
            except Exception: pass
        except ValueError:
            bot.send_message(message.chat.id, "❌ နံပါတ်သာ ရိုက်ထည့်ပါ။ ကျေးဇူးပြု၍ ထပ်ကြိုးစားပါ:")

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
        user_link = f"[{str(r[1])}](tg://user?id={r[5]})"
        
        txt = f"📦 **အော်ဒါနံပါတ်:** #ORD-{r[0]:03d}\n"
        txt += f"👤 **ဝယ်သူ:** {user_link} (ID: `{r[5]}`)\n"
        txt += f"🛍 **မှာယူသည့်အရာ:** `{phone_txt}`\n"
        txt += f"💰 **ကျသင့်ငွေ:** {r[3]:,.0f} ကျပ်\n"
        txt += f"📍 **လိပ်စာ/အချက်အလက်:** {r[4]}"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("✅ ပြီးစီးပါပြီ (Completed)", callback_data="admin_comp_ord_" + str(r[0])),
            types.InlineKeyboardButton("❌ ဤအော်ဒါကို Cancel မည်", callback_data="admin_cancel_ord_" + str(r[0]))
        )
        bot.send_message(message.chat.id, txt, reply_markup=markup, parse_mode="Markdown")

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
            bot.edit_message_text(f"✅ **အော်ဒါ #ORD-{oid:03d} ကို အောင်မြင်စွာ ပို့ဆောင်ပြီးပါပြီ။**", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            
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
            c.execute("UPDATE orders SET status='CANCELLED' WHERE id=?", (oid,))
            conn.commit()
            
            phone_txt = str(phone)
            bot.answer_callback_query(call.id, "အော်ဒါကို ပယ်ဖျက်လိုက်ပါပြီ။", show_alert=True)
            bot.edit_message_text(f"❌ **အော်ဒါ #ORD-{oid:03d} ကို Admin မှ Cancel လိုက်ပါသည်။**", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            
            try:
                bot.send_message(user_id, f"⚠️ တောင်းပန်အပ်ပါသည်။\n\nသင်၏ အော်ဒါ #ORD-{oid:03d} (`{phone_txt}`) ကို Admin မှ ပယ်ဖျက် (Cancel) လိုက်ပါသည်။")
            except Exception: pass

@bot.message_handler(commands=['cancel'])
def admin_cancel_command(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        oid = int(message.text.replace("/cancel", "").strip())
        with sqlite3.connect('vip_shop.db') as conn:
            c = conn.cursor()
            ord_data = c.execute("SELECT ref_id, user_id, chosen_number FROM orders WHERE id=? AND status='PENDING'", (oid,)).fetchone()
            
            if ord_data:
                ref_id, user_id, phone = ord_data
                if ref_id:
                    c.execute("UPDATE numbers SET status='AVAILABLE' WHERE id=?", (ref_id,))
                c.execute("UPDATE orders SET status='CANCELLED' WHERE id=?", (oid,))
                conn.commit()
                
                bot.send_message(message.chat.id, f"✅ အော်ဒါ #ORD-{oid:03d} ကို အောင်မြင်စွာ Cancel လုပ်လိုက်ပါပြီ။")
                try:
                    bot.send_message(user_id, f"⚠️ တောင်းပန်အပ်ပါသည်။\n\nသင်၏ အော်ဒါ #ORD-{oid:03d} (`{phone}`) ကို Admin မှ ပယ်ဖျက် (Cancel) လိုက်ပါသည်။")
                except Exception: pass
            else:
                bot.send_message(message.chat.id, "❌ ဤအော်ဒါနံပါတ် မရှိပါ (သို့မဟုတ်) PENDING အခြေအနေမဟုတ်ပါ။")
    except Exception:
        bot.send_message(message.chat.id, "❌ မှားယွင်းနေပါသည်။ ဥပမာ - `/cancel 15` ဟု ရိုက်ထည့်ပါ။", parse_mode="Markdown")

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
    
    title = f"🗑️ **ပစ္စည်းများ ဖျက်ရန်** ({page+1}/{tpages})\n\n*(ဖျက်လိုသော ပစ္စည်းကို နှိပ်ပါ)*"
    try:
        if is_edit: bot.edit_message_text(title, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
        else: bot.send_message(chat_id, title, reply_markup=markup, parse_mode="Markdown")
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
            bot.send_message(message.chat.id, f"❌ ရောင်းရန်စာရင်းထဲတွင် '{item_name}' ကို မတွေ့ပါ။")
            return
        c.execute("DELETE FROM numbers WHERE phone_number=? AND status='AVAILABLE'", (item_name,))
        conn.commit()
    bot.send_message(message.chat.id, f"✅ '{item_name}' ကို အောင်မြင်စွာ ဖျက်လိုက်ပါပြီ။")

@bot.callback_query_handler(func=lambda call: call.data == "admin_do_backup")
def callback_admin_backup(call):
    if call.from_user.id != ADMIN_ID: return
    try:
        with open('vip_shop.db', 'rb') as f:
            bot.send_document(call.message.chat.id, f, caption="📦 Database Backup ဖိုင်ရပါပြီ။")
            bot.answer_callback_query(call.id, "Backup ဖိုင် ပို့ပေးလိုက်ပါပြီ။")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Error: " + str(e))

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
            bot.send_message(message.chat.id, "❌ Restore ပြလုပ်ရာတွင် အမှားဖြစ်နေပါသည်: " + str(e))

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
        bot.send_message(message.chat.id, f"✅ ဖုန်းနံပါတ် {phone} ({op}) ထည့်ပြီးပါပြီ။")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Error: " + str(e))

@bot.message_handler(commands=['addacc'])
def admin_add_acc(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        content = message.text.replace("/addacc", "").strip()
        parts = [p.strip() for p in content.split(',')]
        
        if len(parts) < 4:
            bot.send_message(message.chat.id, "❌ ပုံစံမှားနေပါသည်။\n\n📌 **AUTO:**\n`/addacc အမည်, ဈေးနှုန်း, Platform, AUTO, အချက်အလက်`\n\n📌 **MANUAL:**\n`/addacc အမည်, ဈေးနှုန်း, Platform, MANUAL`", parse_mode="Markdown")
            return
        
        acc_name = parts[0]
        price = float(parts[1])
        platform = parts[2]
        mode = parts[3].upper()
        
        digital_info = ""
        if mode == "AUTO":
            if len(parts) < 5:
                bot.send_message(message.chat.id, "❌ AUTO အတွက် ပေးမည့် အချက်အလက် ထည့်ရန် မေ့နေပါသည်။")
                return
            digital_info = parts[4]
            ntype = "DIGITAL_AUTO"
        else:
            ntype = "DIGITAL_MANUAL"
        
        with sqlite3.connect('vip_shop.db') as conn:
            conn.cursor().execute("INSERT INTO numbers (phone_number, operator, price, num_type, digital_info) VALUES (?, ?, ?, ?, ?)", (acc_name, platform, price, ntype, digital_info))
            conn.commit()
            
        bot.send_message(message.chat.id, f"✅ Digital Acc ('{acc_name}' - {mode}) အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ။")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Error: " + str(e))

@bot.message_handler(func=lambda m: m.text == "📞 ဆိုင်နှင့် ဆက်သွယ်ရန်")
def contact_shop(message):
    text = "📞 **Star Mobile VIP Shop**\n\n" + \
           "💬 Telegram Admin: @orange310199\n" + \
           "💳 **Wave:** `09 792 654 163` (Si Thu Aung)\n" + \
           "💳 **Kpay:** `09 79 50 96 484` (Si Thu Aung)\n" + \
           "⏰ အလုပ်ချိန်: မနက် ၉ နာရီ မှ ည ၉ နာရီအထိ"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "✨ နံပါတ်လှများကြည့်မည်")
@require_channel_join
def show_pro_numbers(message):
    send_paginated_numbers(message.chat.id, "PRO", 0)

@bot.message_handler(func=lambda m: m.text == "🍀 Lucky Phone ကြည့်မည်")
@require_channel_join
def show_lucky_numbers(message):
    send_paginated_numbers(message.chat.id, "LUCKY", 0)

@bot.message_handler(func=lambda m: m.text == "🎮 Digital Acc များ")
@require_channel_join
def show_digital_accs(message):
    send_paginated_digital(message.chat.id, 0)

def send_paginated_digital(chat_id, page, is_edit=False, message_id=None):
    with sqlite3.connect('vip_shop.db') as conn:
        c = conn.cursor()
        tot = c.execute("SELECT COUNT(DISTINCT phone_number) FROM numbers WHERE num_type='DIGITAL_AUTO' AND status='AVAILABLE'").fetchone()[0]
        manual_tot = c.execute("SELECT COUNT(*) FROM numbers WHERE num_type='DIGITAL_MANUAL' AND status='AVAILABLE'").fetchone()[0]
        total_items = tot + manual_tot
        
        if total_items == 0:
            if is_edit: bot.edit_message_text("📭 စာရင်း မရှိသေးပါ။", chat_id, message_id)
            else: bot.send_message(chat_id, "📭 စာရင်း မရှိသေးပါ။")
            return
            
        tpages = math.ceil(total_items / ITEMS_PER_PAGE)
        
        auto_rows = c.execute("SELECT MIN(id), phone_number, operator, price, COUNT(*) as stock FROM numbers WHERE num_type='DIGITAL_AUTO' AND status='AVAILABLE' GROUP BY phone_number, operator, price ORDER BY price ASC").fetchall()
        manual_rows = c.execute("SELECT id, phone_number, operator, price, 1 as stock FROM numbers WHERE num_type='DIGITAL_MANUAL' AND status='AVAILABLE' ORDER BY price ASC").fetchall()
        
        all_rows = auto_rows + manual_rows
        paged_rows = all_rows[page * ITEMS_PER_PAGE : (page + 1) * ITEMS_PER_PAGE]

    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in paged_rows:
        item_id = r[0]
        name = r[1]
        platform = r[2]
        price = r[3]
        stock = r[4]
        
        if stock > 1:
            btn_text = f"🎮 {name} ( Stock: {stock} ) - {price:,.0f} ကျပ်"
        else:
            btn_text = f"🎮 {name} ({platform}) - {price:,.0f} ကျပ်"
            
        markup.add(types.InlineKeyboardButton(btn_text, callback_data="buy_" + str(item_id)))

    nav = []
    if page > 0: nav.append(types.InlineKeyboardButton("⬅️ ရှေ့သို့", callback_data="digipage_" + str(page-1)))
    if page < tpages - 1: nav.append(types.InlineKeyboardButton("နောက်သို့ ➡️", callback_data="digipage_" + str(page+1)))
    if nav: markup.row(*nav)

    title = f"🎮 **Digital Accounts** ({page+1}/{tpages})"
    if is_edit: bot.edit_message_text(title, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
    else: bot.send_message(chat_id, title, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("digipage_"))
def handle_digi_pagination(call):
    page = int(call.data.split("_")[1])
    send_paginated_digital(call.message.chat.id, page, True, call.message.message_id)

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
        markup.add(types.InlineKeyboardButton(f"{phone_txt} ({r[2]}) - {r[3]:,.0f} ကျပ်", callback_data="buy_" + str(r[0])))

    nav = []
    if page > 0: nav.append(types.InlineKeyboardButton("⬅️ ရှေ့သို့", callback_data="page_" + n_type + "_" + str(page-1)))
    if page < tpages - 1: nav.append(types.InlineKeyboardButton("နောက်သို့ ➡️", callback_data="page_" + n_type + "_" + str(page+1)))
    if nav: markup.row(*nav)

    title_prefix = "✨ နံပါတ်လှများ" if n_type == "PRO" else "🍀 Lucky Phone"
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
        markup.add(types.InlineKeyboardButton(f"{phone_txt} - {r[2]:,.0f} ကျပ်", callback_data="buy_" + str(r[0])))

    nav = []
    if page > 0: nav.append(types.InlineKeyboardButton("⬅️ ရှေ့သို့", callback_data="oppage_" + op + "_" + str(page-1)))
    if page < tpages - 1: nav.append(types.InlineKeyboardButton("နောက်သို့ ➡️", callback_data="oppage_" + op + "_" + str(page+1)))
    if nav: markup.row(*nav)

    title = f"📡 *{op}* နံပါတ်များ ({page+1}/{tpages})"
    if is_edit: bot.edit_message_text(title, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
    else: bot.send_message(chat_id, title, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("op_"))
def filter_by_operator(call):
    op = call.data.split("_")[1]
    send_paginated_operators(call.message.chat.id, op, 0, True, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("oppage_"))
def handle_op_pagination(call):
    p = call.data.split("_")
    send_paginated_operators(call.message.chat.id, p[1], int(p[2]), True, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def process_buy(call):
    nid = int(call.data.split("_")[1])
    uid = call.from_user.id
    
    with sqlite3.connect('vip_shop.db') as conn:
        c = conn.cursor()
        item = c.execute("SELECT id, phone_number, price, status, num_type FROM numbers WHERE id=?", (nid,)).fetchone()
        user_bal = c.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
        
    if not item or (item[3] == 'SOLD' and item[4] not in ['DIGITAL_AUTO', 'DIGITAL_MANUAL']):
        bot.answer_callback_query(call.id, "ဤပစ္စည်း မရှိတော့ပါ။", show_alert=True)
        return
        
    if item[4] == 'DIGITAL_AUTO':
        with sqlite3.connect('vip_shop.db') as conn:
            actual_item = conn.cursor().execute("SELECT id, phone_number, price FROM numbers WHERE phone_number=? AND num_type='DIGITAL_AUTO' AND status='AVAILABLE' LIMIT 1", (item[1],)).fetchone()
            if not actual_item:
                bot.answer_callback_query(call.id, "ဤပစ္စည်း Stock ကုန်သွားပါပြီ။", show_alert=True)
                return
            nid = actual_item[0]
            phone_txt = actual_item[1]
            price = actual_item[2]
    else:
        phone_txt = str(item[1])
        price = item[2]
        
    balance = user_bal[0] if user_bal else 0
    ntype = str(item[4])
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # 📌 ဖုန်းနံပါတ်များ (PRO, LUCKY, Operator) ဖြစ်ပါက Point ဖြင့် ငွေချေသည့်ခလုတ် မပါဝင်စေဘဲ ငွေလွှဲစနစ်ဖြင့်သာ ဝယ်ယူစေမည်
    if balance >= price and ntype in ['DIGITAL_AUTO', 'DIGITAL_MANUAL']:
        if ntype == 'DIGITAL_AUTO':
            markup.add(types.InlineKeyboardButton(f"💳 လက်ကျန်ငွေ (Points) ဖြင့် ငွေချေမည် ({balance:,.0f} Ks)", callback_data=f"paypoints_auto_{nid}"))
        elif ntype == 'DIGITAL_MANUAL':
            markup.add(types.InlineKeyboardButton(f"💳 လက်ကျန်ငွေ (Points) ဖြင့် ငွေချေမည် ({balance:,.0f} Ks)", callback_data=f"paypoints_manual_{nid}"))
            
    if ntype == "DIGITAL_AUTO":
        markup.add(
            types.InlineKeyboardButton("📤 SS ပို့မည်", callback_data="prompt_digi_ss_" + str(nid)),
            types.InlineKeyboardButton("❌ မဝယ်တော့ပါ", callback_data="cancel_buy_" + str(nid))
        )
        txt = f"🎮 **ရွေးချယ်ထားသော အကောင့်:** {phone_txt}\n💰 **ကျသင့်ငွေ:** {price:,.0f} ကျပ်\n👛 သင်၏လက်ကျန်ငွေ: {balance:,.0f} ကျပ်\n\n" \
              f"💳 **ငွေလွှဲရန်:**\nWave: `09 792 654 163` (Si Thu Aung)\nKpay: `09 79 50 96 484` (Si Thu Aung)"
        bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        
    elif ntype == "DIGITAL_MANUAL":
        markup.add(
            types.InlineKeyboardButton("✅ သေချာပါသည် ဝယ်ယူမည်", callback_data="confdigi_manual_" + str(nid)),
            types.InlineKeyboardButton("❌ မဝယ်တော့ပါ", callback_data="cancel_buy_" + str(nid))
        )
        txt = f"🎮 **ရွေးချယ်ထားသော အကောင့်:** {phone_txt}\n💰 **ကျသင့်ငွေ:** {price:,.0f} ကျပ်\n👛 သင်၏လက်ကျန်ငွေ: {balance:,.0f} ကျပ်\n\n⚠️ Admin ကိုယ်တိုင် ဆောင်ရွက်ပေးရမည့် အမျိုးအစား ဖြစ်ပါသည်။"
        bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        
    else:
        markup.add(types.InlineKeyboardButton("❌ မဝယ်တော့ပါ", callback_data="cancel_buy_" + str(nid)))
        txt = f"🎯 ရွေးချယ်ထားသောပစ္စည်း: {phone_txt}\n💰 ဈေးနှုန်း: {price:,.0f} ကျပ်\n\n" \
              f"💳 **Deli ခ 4,000 နှင့် တန်ဖိုးငွေ လွှဲရန်:**\nWave: `09 792 654 163`\nKpay: `09 79 50 96 484`\n\n📝 နာမည်၊ ဖုန်း၊ လိပ်စာ အတိအကျ ရိုက်ထည့်ပေးပါ -"
        
        msg = bot.send_message(call.message.chat.id, txt, reply_markup=markup)
        bot.register_next_step_handler(msg, save_order, phone_txt, price, nid)

@bot.callback_query_handler(func=lambda call: call.data.startswith("prompt_digi_ss_"))
def prompt_digi_ss(call):
    nid = int(call.data.split("_")[3])
    msg = bot.send_message(call.message.chat.id, "🖼️ ကျေးဇူးပြု၍ ငွေလွှဲထားသော Screenshot (SS) ပုံကို ပို့ပေးပါ။")
    bot.register_next_step_handler(msg, receive_digi_order_ss, nid)

def receive_digi_order_ss(message, nid):
    if message.content_type != 'photo':
        msg = bot.send_message(message.chat.id, "❌ ကျေးဇူးပြု၍ ပုံ (Photo) သာ ပို့ပေးပါ။ ကျေးဇူးပြု၍ SS ပုံကို ထပ်မံပို့ပေးပါ:")
        bot.register_next_step_handler(msg, receive_digi_order_ss, nid)
        return
        
    photo_id = message.photo[-1].file_id
    uid = message.from_user.id
    fname = message.from_user.first_name
    
    with sqlite3.connect('vip_shop.db') as conn:
        item = conn.cursor().execute("SELECT phone_number, price FROM numbers WHERE id=?", (nid,)).fetchone()
        if not item:
            bot.send_message(message.chat.id, "❌ ဤပစ္စည်း မရှိတော့ပါ။")
            return
        phone = item[0]
        price = item[1]
        
    user_link = f"[{fname}](tg://user?id={uid})"
    admin_txt = f"🎮 **Digital အော်ဒါ (ငွေလွှဲ SS ပို့ထားသည်)**\n\n👤 ဝယ်သူ: {user_link}\n🆔 User ID: `{uid}`\n🛍 အကောင့်: {phone}\n💰 ဈေးနှုန်း: {price:,.0f} ကျပ်"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("✅ ခွင့်ပြုသည်", callback_data=f"admin_app_digi_{nid}_{uid}"),
        types.InlineKeyboardButton("❌ ပယ်မည်", callback_data=f"admin_rej_digi_{nid}_{uid}")
    )
    
    try:
        bot.send_photo(ADMIN_ID, photo_id, caption=admin_txt, reply_markup=markup, parse_mode="Markdown")
        bot.send_message(message.chat.id, "✅ ငွေလွှဲပြေစာ ပို့ခြင်း အောင်မြင်ပါသည်။ Admin မှ စစ်ဆေးပြီးပါက အကောင့်အချက်အလက်ကို ပို့ပေးပါမည်။")
    except Exception:
        bot.send_message(message.chat.id, "❌ ပို့ဆောင်ရာတွင် အမှားဖြစ်နေပါသည်၊ ထပ်မံကြိုးစားပါ။")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_app_digi_"))
def admin_approve_digital_order(call):
    if call.from_user.id != ADMIN_ID: return
    parts = call.data.split("_")
    nid = int(parts[3])
    user_id = int(parts[4])
    
    with sqlite3.connect('vip_shop.db') as conn:
        c = conn.cursor()
        item = c.execute("SELECT phone_number, price, digital_info FROM numbers WHERE id=?", (nid,)).fetchone()
        if not item:
            bot.answer_callback_query(call.id, "ပစ္စည်း မရှိတော့ပါ။", show_alert=True)
            return
        phone = item[0]
        price = item[1]
        digi_info = item[2]
        
        c.execute("UPDATE numbers SET status='SOLD' WHERE id=?", (nid,))
        c.execute("INSERT INTO orders (user_id, customer_name, chosen_number, price, contact_info, ref_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)", (user_id, "Customer", phone, price, "Digital Auto Delivery (Bank Approved)", nid, "COMPLETED"))
        conn.commit()
        oid = c.lastrowid
        
    bot.answer_callback_query(call.id, "အော်ဒါကို ခွင့်ပြုပြီး အကောင့်ပို့လိုက်ပါပြီ။")
    bot.edit_message_caption(caption=call.message.caption + "\n\n✅ **[ခွင့်ပြုပြီး အကောင့်ပို့ပြီးပါပြီ]**", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
    
    try:
        txt = f"🎉 **ဝယ်ယူမှု အောင်မြင်ပါသည်။** (#ORD-{oid:03d})\n\n"
        txt += f"🎮 **အကောင့်:** {phone}\n"
        txt += f"🔑 **အချက်အလက် (Account Info):**\n`{digi_info}`\n\n"
        txt += f"ကျေးဇူးတင်ပါတယ်။ အချက်အလက်များကို Copy ကူးယူနိုင်ပါပြီ။"
        bot.send_message(user_id, txt, parse_mode="Markdown")
    except Exception: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_rej_digi_"))
def admin_reject_digital_order(call):
    if call.from_user.id != ADMIN_ID: return
    parts = call.data.split("_")
    user_id = int(parts[4])
    
    bot.answer_callback_query(call.id, "အော်ဒါကို ပယ်ချလိုက်ပါပြီ။")
    bot.edit_message_caption(caption=call.message.caption + "\n\n❌ **[ပယ်ချလိုက်ပါပြီ]**", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
    
    try:
        bot.send_message(user_id, "⚠️ တောင်းပန်ပါတယ်၊ သင်တင်ပြလာသော ငွေလွှဲပြေစာ (SS) မမှန်ကန်ပါသဖြင့် အော်ဒါကို ပယ်ချလိုက်ပါသည်။")
    except Exception: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("paypoints_auto_"))
def pay_points_auto(call):
    nid = int(call.data.split("_")[2])
    uid = call.from_user.id
    fname = call.from_user.first_name
    
    with sqlite3.connect('vip_shop.db') as conn:
        c = conn.cursor()
        item = c.execute("SELECT phone_number, price, digital_info FROM numbers WHERE id=? AND status='AVAILABLE'", (nid,)).fetchone()
        user = c.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
        
        if not item or not user:
            bot.answer_callback_query(call.id, "ပစ္စည်း မရှိတော့ပါ သို့မဟုတ် အကောင့်အချက်အလက် မှားယွင်းနေပါသည်။", show_alert=True)
            return
            
        phone = item[0]
        price = item[1]
        digi_info = item[2]
        balance = user[0]
        
        if balance < price:
            bot.answer_callback_query(call.id, "လက်ကျန်ငွေ (Points) မလုံလောက်ပါ။", show_alert=True)
            return
            
        c.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (price, uid))
        c.execute("UPDATE numbers SET status='SOLD' WHERE id=?", (nid,))
        c.execute("INSERT INTO orders (user_id, customer_name, chosen_number, price, contact_info, ref_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)", (uid, fname, phone, price, "Paid with Points (Auto)", nid, "COMPLETED"))
        conn.commit()
        oid = c.lastrowid
        
    bot.answer_callback_query(call.id, "Points ဖြင့် ငွေချေမှု အောင်မြင်ပါသည်။")
    
    txt = f"🎉 **ဝယ်ယူမှု အောင်မြင်ပါသည်။** (#ORD-{oid:03d})\n\n"
    txt += f"🎮 **အကောင့်:** {phone}\n"
    txt += f"🔑 **အချက်အလက် (Account Info):**\n`{digi_info}`\n\n"
    txt += f"ကျေးဇူးတင်ပါတယ်။ အချက်အလက်များကို Copy ကူးယူနိုင်ပါပြီ။"
    
    bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    
    try:
        user_link = f"[{fname}](tg://user?id={uid})"
        bot.send_message(ADMIN_ID, f"🔔 **Digital (AUTO - Points ဖြင့်ဝယ်) ရောင်းထွက်သည်:** #ORD-{oid:03d}\n👤 ဝယ်သူ: {user_link}\n🛍 အကောင့်: {phone}\n💰 ဈေးနှုန်း: {price:,.0f} ကျပ်", parse_mode="Markdown")
    except Exception: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("paypoints_manual_"))
def pay_points_manual(call):
    nid = int(call.data.split("_")[2])
    uid = call.from_user.id
    fname = call.from_user.first_name
    
    with sqlite3.connect('vip_shop.db') as conn:
        c = conn.cursor()
        item = c.execute("SELECT phone_number, price FROM numbers WHERE id=? AND status='AVAILABLE'", (nid,)).fetchone()
        user = c.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
        
        if not item or not user:
            bot.answer_callback_query(call.id, "ပစ္စည်း မရှိတော့ပါ။", show_alert=True)
            return
            
        phone = item[0]
        price = item[1]
        balance = user[0]
        
        if balance < price:
            bot.answer_callback_query(call.id, "လက်ကျန်ငွေ (Points) မလုံလောက်ပါ။", show_alert=True)
            return
            
        c.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (price, uid))
        c.execute("INSERT INTO orders (user_id, customer_name, chosen_number, price, contact_info, ref_id) VALUES (?, ?, ?, ?, ?, ?)", (uid, fname, phone, price, "Paid with Points (Manual)", nid))
        conn.commit()
        oid = c.lastrowid
        
    bot.answer_callback_query(call.id, "Points ဖြင့် ငွေချေမှု အောင်မြင်ပါသည်။")
    
    txt = f"✅ **အော်ဒါတင်ခြင်း အောင်မြင်ပါသည်။** (#ORD-{oid:03d})\n\n"
    txt += f"🎮 **ပစ္စည်း:** {phone}\n💰 **ကျသင့်ငွေ:** {price:,.0f} ကျပ် (Points မှ ဖြတ်တောက်ပြီးပါပြီ)\n\n"
    txt += f"💬 ကျေးဇူးပြု၍ Admin 👉 @orange310199 ထံသို့ Message ပို့၍ ဝန်ဆောင်မှုရယူပါ။"
    
    bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    
    try:
        user_link = f"[{fname}](tg://user?id={uid})"
        admin_msg = f"🔔 **အော်ဒါသစ် (Points ဖြင့်ပေးချေပြီး):** #ORD-{oid:03d}\n👤 ဝယ်သူ: {user_link}\n🛍 မှာယူသည့်အရာ: {phone}\n💰 ဈေးနှုန်း: {price:,.0f} ကျပ်"
        admin_markup = types.InlineKeyboardMarkup(row_width=1)
        admin_markup.add(
            types.InlineKeyboardButton("✅ ပြီးစီးပါပြီ (Completed)", callback_data=f"admin_comp_ord_{oid}"),
            types.InlineKeyboardButton("❌ ဤအော်ဒါကို Cancel မည်", callback_data=f"admin_cancel_ord_{oid}")
        )
        bot.send_message(ADMIN_ID, admin_msg, reply_markup=admin_markup, parse_mode="Markdown")
    except Exception: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_buy_"))
def user_cancel_buy(call):
    bot.clear_step_handler_by_chat_id(call.message.chat.id)
    bot.send_message(call.message.chat.id, "ဝယ်ယူမှုကို ပယ်ဖျက်လိုက်ပါပြီ။", reply_markup=main_menu(call.from_user.id))

def save_order(message, phone, price, nid):
    if message.text in ["✨ နံပါတ်လှများကြည့်မည်", "🍀 Lucky Phone ကြည့်မည်", "📡 Operator အလိုက်ကြည့်မည်", "🎮 Digital Acc များ", "👛 မိမိအကောင့်", "📞 ဆိုင်နှင့် ဆက်သွယ်ရန်", "👑 Admin Panel"]:
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
        
    success_txt = f"✅ **အော်ဒါတင်ခြင်း အောင်မြင်ပါသည်။** (#ORD-{oid:03d})\n\n"
    success_txt += f"💬 ကျေးဇူးပြု၍ ငွေလွှဲပြေစာ (Screenshot) ကို Admin 👉 @orange310199 ထံသို့ ပေးပို့ပေးပါ။\n"
    success_txt += f"⏱ Admin မှ အမြန်ဆုံး ပြန်လည်အကြောင်းပြန်ပေးပါမည်။ ကျေးဇူးတင်ပါတယ်။"
    bot.send_message(message.chat.id, success_txt, parse_mode="Markdown")
    
    try:
        phone_txt = str(phone)
        user_link = f"[{fname}](tg://user?id={uid})"
        admin_msg = f"🔔 **အော်ဒါသစ်:** #ORD-{oid:03d}\n👤 ဝယ်သူ: {user_link}\n🛍 မှာယူသည့်အရာ: {phone_txt}\n💰 ဈေးနှုန်း: {price:,.0f} ကျပ်\n📍 လိပ်စာ: {str(info)}"
        
        admin_markup = types.InlineKeyboardMarkup(row_width=1)
        admin_markup.add(
            types.InlineKeyboardButton("✅ ပြီးစီးပါပြီ (Completed)", callback_data=f"admin_comp_ord_{oid}"),
            types.InlineKeyboardButton("❌ ဤအော်ဒါကို Cancel မည်", callback_data=f"admin_cancel_ord_{oid}")
        )
        bot.send_message(ADMIN_ID, admin_msg, reply_markup=admin_markup, parse_mode="Markdown")
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
