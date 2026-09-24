import os
import telebot
from telebot import types
import math
import logging
import threading
from flask import Flask
import time
import requests
import pymongo
from bson.objectid import ObjectId
from datetime import datetime

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "8753076212:AAE0V-dfeaioWbCYUAwcpJuw9MnDtISLzbU"
ADMIN_ID = 8668319365
CHANNEL_USERNAME = "@starmobile63956"
ITEMS_PER_PAGE = 10

bot = telebot.TeleBot(TOKEN)

pending_order_address = {}
waiting_for_restore = {}

# ==========================================
# 🗄️ MongoDB ချိတ်ဆက်ခြင်း (Cloud Database)
# ==========================================
# သင့်ရဲ့ MongoDB URI ကို အောက်ပါနေရာမှာ ထည့်ပါ။
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://User:310199@cluster0.oys0fgi.mongodb.net/?appName=Cluster0")
client = pymongo.MongoClient(MONGO_URI)
db = client["vip_shop"]

# ==========================================
# 🌐 Flask Server (Keep Alive)
# ==========================================
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
            render_url = os.environ.get("RENDER_EXTERNAL_URL")
            if render_url:
                requests.get(render_url)
            else:
                requests.get(f"http://127.0.0.1:{PORT}")
        except Exception:
            pass
        time.sleep(14 * 60)

threading.Thread(target=keep_alive_ping, daemon=True).start()

# --- အော်ဒါနံပါတ်စဉ် အတွက် Auto-Increment ---
def get_next_order_id():
    ret = db.counters.find_one_and_update(
        {'_id': 'order_id'},
        {'$inc': {'seq': 1}},
        upsert=True,
        return_document=pymongo.ReturnDocument.AFTER
    )
    return ret['seq']

def register_user(user_id, first_name):
    db.users.update_one({'user_id': user_id}, {'$set': {'first_name': first_name}}, upsert=True)

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
    except Exception: 
        return True
    return False

def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("✨ နံပါတ်လှများကြည့်မည်", "🍀 Lucky Phone ကြည့်မည်")
    markup.add("📡 Operator အလိုက်ကြည့်မည်", "🎮 Digital Acc များ") 
    markup.add("🔍 နံပါတ်ရှာဖွေမည်", "🛒 ကျွန်ုပ်၏ အော်ဒါများ") 
    markup.add("📞 ဆိုင်နှင့် ဆက်သွယ်ရန်")
    if user_id == ADMIN_ID: markup.add("👑 Admin Panel")
    return markup

def not_joined_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📢 Channel သို့သွားရန်", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"),
        types.InlineKeyboardButton("✅ Join ပြီးပါပြီ (စစ်ဆေးမည်)", callback_data="check_join")
    )
    return markup

def broadcast_to_users(text=None, original_message=None):
    users = db.users.find({}, {"user_id": 1})
    succ = 0
    for u in users:
        try:
            if text:
                bot.send_message(u["user_id"], text, parse_mode="Markdown")
            elif original_message:
                bot.copy_message(u["user_id"], original_message.chat.id, original_message.message_id)
            succ += 1
        except Exception as e:
            if "bot was blocked" in str(e).lower() or "deactivated" in str(e).lower():
                db.users.delete_one({"user_id": u["user_id"]})
    return succ

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
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
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

# ==========================================
# 👑 ADMIN PANEL & CONTROL BUTTONS
# ==========================================
@bot.message_handler(func=lambda m: m.text == "👑 Admin Panel")
def show_admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    text = "👑 **Admin Control Panel**\n\n" + \
           "📌 **ဖုန်းနံပါတ်အသစ်ထည့်ရန်:** `/addnum နံပါတ်, ဈေးနှုန်း, အမျိုးအစား(PRO/LUCKY)`\n" + \
           "📌 **Digital Acc အသစ်ထည့်ရန်:** `/addacc အမည်, ဈေးနှုန်း, Platform, AUTO/MANUAL, အချက်အလက်`\n" + \
           "📌 **Broadcast ပို့ရန်:** ဓာတ်ပုံ/စာ ကို Reply ပြန်ပြီး `/broadcast` ဟုရိုက်ပါ။\n" + \
           "📌 **ပစ္စည်းဖျက်ရန်:** `/del` | **အော်ဒါ Cancel ရန်:** `/cancel အော်ဒါနံပါတ်`"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📦 PENDING အော်ဒါဟောင်းများ ကြည့်ရန်", callback_data="admin_view_orders"),
        types.InlineKeyboardButton("📊 အရောင်းစာရင်း (Sales Report)", callback_data="admin_sales_report"),
        types.InlineKeyboardButton("🗑️ ရောင်းရန်ရှိသည့် ပစ္စည်းများဖျက်ရန်", callback_data="admin_del_list_0"),
        types.InlineKeyboardButton("⚠️ စာရင်းအားလုံး ရှင်းလင်းမည် (Reset)", callback_data="admin_reset_confirm"),
        types.InlineKeyboardButton("💾 Database အခြေအနေ", callback_data="admin_db_status")
    )
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_reset_confirm")
def admin_reset_confirm(call):
    if call.from_user.id != ADMIN_ID: return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ ဟုတ်ကဲ့၊ အားလုံးဖျက်မည်", callback_data="admin_reset_procced"),
        types.InlineKeyboardButton("❌ မလုပ်တော့ပါ", callback_data="admin_reset_cancel")
    )
    bot.edit_message_text("⚠️ **သတိပေးချက်!**\n\nပစ္စည်းစာရင်းများ (Numbers) နှင့် အော်ဒါမှတ်တမ်းများ (Orders) အားလုံး လုံးဝ ပျက်ပြယ်သွားမည် ဖြစ်ပါသည်။ ဆက်လုပ်ရန် သေချာပါသလား?", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_reset_procced")
def admin_reset_procced(call):
    if call.from_user.id != ADMIN_ID: return
    db.numbers.delete_many({})
    db.orders.delete_many({})
    bot.answer_callback_query(call.id, "စာရင်းအားလုံး အောင်မြင်စွာ ရှင်းလင်းပြီးပါပြီ။", show_alert=True)
    bot.edit_message_text("✅ **ဒေတာစာရင်းအားလုံး ကို အောင်မြင်စွာ ရှင်းလင်း (Reset) ပြီးပါပြီ။**", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_reset_cancel")
def admin_reset_cancel(call):
    if call.from_user.id != ADMIN_ID: return
    bot.answer_callback_query(call.id, "ပယ်ဖျက်လိုက်ပါပြီ။")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_admin_panel(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "admin_sales_report")
def admin_sales_report(call):
    if call.from_user.id != ADMIN_ID: return
    bot.answer_callback_query(call.id, "စာရင်း တွက်ချက်နေပါသည်...")
    
    total_data = list(db.orders.aggregate([
        {'$match': {'status': 'COMPLETED'}},
        {'$group': {'_id': None, 'total_rev': {'$sum': '$price'}, 'count': {'$sum': 1}}}
    ]))
    
    total_rev = total_data[0]['total_rev'] if total_data else 0
    total_orders = total_data[0]['count'] if total_data else 0
    
    monthly_data = list(db.orders.aggregate([
        {'$match': {'status': 'COMPLETED'}},
        {'$group': {
            '_id': {'$dateToString': {'format': "%Y-%m", 'date': "$date"}},
            'total_rev': {'$sum': '$price'},
            'count': {'$sum': 1}
        }},
        {'$sort': {'_id': -1}}
    ]))
        
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
            text += f"🔹 **{r['_id']}** : {r['total_rev']:,.0f} ကျပ် ({r['count']} ခု)\n"
            
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_view_orders")
def admin_view_orders(call):
    if call.from_user.id != ADMIN_ID: return
    orders = list(db.orders.find({'status': 'PENDING'}))
    
    if not orders:
        bot.answer_callback_query(call.id, "လောလောဆယ် PENDING အော်ဒါ မရှိပါ။", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    for r in orders:
        txt = f"📦 **အော်ဒါနံပါတ်:** #ORD-{r['order_id']:03d}\n"
        txt += f"👤 **ဝယ်သူ:** [{str(r.get('customer_name',''))}](tg://user?id={r['user_id']}) (ID: `{r['user_id']}`)\n"
        txt += f"🛍 **မှာယူသည့်အရာ:** `{str(r['chosen_number'])}`\n"
        txt += f"💰 **ကျသင့်ငွေ:** {r['price']:,.0f} ကျပ်\n"
        txt += f"📍 **လိပ်စာ/အချက်အလက်:** {r.get('contact_info', '')}"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("✅ ပြီးစီးပါပြီ (Completed)", callback_data="admin_comp_ord_" + str(r['order_id'])),
            types.InlineKeyboardButton("❌ ဤအော်ဒါကို Cancel မည်", callback_data="admin_cancel_ord_" + str(r['order_id']))
        )
        bot.send_message(call.message.chat.id, txt, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_comp_ord_"))
def admin_complete_order(call):
    if call.from_user.id != ADMIN_ID: return
    oid = int(call.data.split("_")[3])
    
    ord_data = db.orders.find_one({'order_id': oid})
    if ord_data:
        db.orders.update_one({'order_id': oid}, {'$set': {'status': 'COMPLETED'}})
        bot.answer_callback_query(call.id, "အော်ဒါ ပြီးစီးကြောင်း မှတ်သားလိုက်ပါပြီ。", show_alert=True)
        
        try:
            if call.message.photo:
                bot.edit_message_caption(caption=call.message.caption + "\n\n✅ **[အော်ဒါ ပြီးစီးပါပြီ (Completed)]**", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
            else:
                bot.edit_message_text(f"✅ **အော်ဒါ #ORD-{oid:03d} ကို အောင်မြင်စွာ ပို့ဆောင်ပြီးပါပြီ။**", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        except Exception: pass
        
        try:
            msg = f"🎉 **ဝမ်းသာစရာ သတင်းပါခင်ဗျာ!**\n\nလူကြီးမင်း၏ အော်ဒါ #ORD-{oid:03d} (`{str(ord_data['chosen_number'])}`) ကို ဆိုင်မှ အောင်မြင်စွာ ပို့ဆောင်ပေးလိုက်ပါပြီ။\n\nအားပေးမှုကို အထူးကျေးဇူးတင်ရှိပါသည်။ 🙏"
            bot.send_message(ord_data['user_id'], msg, parse_mode="Markdown")
        except Exception: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_cancel_ord_"))
def admin_cancel_order(call):
    if call.from_user.id != ADMIN_ID: return
    oid = int(call.data.split("_")[3])
    
    ord_data = db.orders.find_one({'order_id': oid})
    if ord_data:
        if ord_data.get('ref_id'): 
            db.numbers.update_one({'_id': ObjectId(ord_data['ref_id'])}, {'$set': {'status': 'AVAILABLE'}})
        
        db.orders.update_one({'order_id': oid}, {'$set': {'status': 'CANCELLED'}})
        bot.answer_callback_query(call.id, "အော်ဒါကို ပယ်ဖျက်လိုက်ပါပြီ。", show_alert=True)
        
        try:
            if call.message.photo:
                bot.edit_message_caption(caption=call.message.caption + "\n\n❌ **[ဤအော်ဒါကို Cancel လိုက်ပါပြီ]**", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
            else:
                bot.edit_message_text(f"❌ **အော်ဒါ #ORD-{oid:03d} ကို Admin မှ Cancel လိုက်ပါသည်။**", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        except Exception: pass
        
        try:
            bot.send_message(ord_data['user_id'], f"⚠️ တောင်းပန်အပ်ပါသည်။\n\nသင်၏ အော်ဒါ #ORD-{oid:03d} (`{str(ord_data['chosen_number'])}`) ကို Admin မှ ပယ်ဖျက် (Cancel) လိုက်ပါသည်။")
        except Exception: pass

@bot.message_handler(commands=['cancel'])
def admin_cancel_command(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        oid = int(message.text.replace("/cancel", "").strip())
        ord_data = db.orders.find_one({'order_id': oid, 'status': 'PENDING'})
        
        if ord_data:
            if ord_data.get('ref_id'): 
                db.numbers.update_one({'_id': ObjectId(ord_data['ref_id'])}, {'$set': {'status': 'AVAILABLE'}})
            
            db.orders.update_one({'order_id': oid}, {'$set': {'status': 'CANCELLED'}})
            bot.send_message(message.chat.id, f"✅ အော်ဒါ #ORD-{oid:03d} ကို အောင်မြင်စွာ Cancel လုပ်လိုက်ပါပြီ။")
            try:
                bot.send_message(ord_data['user_id'], f"⚠️ တောင်းပန်အပ်ပါသည်။\n\nသင်၏ အော်ဒါ #ORD-{oid:03d} (`{str(ord_data['chosen_number'])}`) ကို Admin မှ ပယ်ဖျက် (Cancel) လိုက်ပါသည်။")
            except Exception: pass
        else:
            bot.send_message(message.chat.id, "❌ ဤအော်ဒါနံပါတ် မရှိပါ (သို့မဟုတ်) PENDING အခြေအနေမဟုတ်ပါ။")
    except Exception:
        bot.send_message(message.chat.id, "❌ မှားယွင်းနေပါသည်၊ ဥပမာ - `/cancel 15` ဟု ရိုက်ထည့်ပါ။", parse_mode="Markdown")

def show_delete_list(chat_id, page, is_edit=False, message_id=None):
    tot = db.numbers.count_documents({'status': 'AVAILABLE'})
    if tot == 0:
        if is_edit: bot.edit_message_text("📭 ရောင်းရန် ပစ္စည်း မရှိသေးပါ။", chat_id, message_id)
        else: bot.send_message(chat_id, "📭 ရောင်းရန် ပစ္စည်း မရှိသေးပါ။")
        return
        
    tpages = math.ceil(tot / ITEMS_PER_PAGE)
    if page >= tpages: page = tpages - 1
    if page < 0: page = 0
        
    rows = list(db.numbers.find({'status': 'AVAILABLE'}).sort('_id', -1).skip(page * ITEMS_PER_PAGE).limit(ITEMS_PER_PAGE))
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        markup.add(types.InlineKeyboardButton(f"🗑 {r['phone_number']} ({r['price']:,.0f} Ks) [{r.get('num_type','')}]", callback_data=f"admin_del_item_{str(r['_id'])}_{page}"))
        
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
    nid, page = parts[3], int(parts[4])
    
    num = db.numbers.find_one({'_id': ObjectId(nid)})
    if num:
        db.numbers.delete_one({'_id': ObjectId(nid)})
        bot.answer_callback_query(call.id, f"✅ '{num['phone_number']}' ကို ဖျက်လိုက်ပါပြီ။", show_alert=False)
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
        
    num = db.numbers.find_one({'phone_number': item_name, 'status': 'AVAILABLE'})
    if not num:
        bot.send_message(message.chat.id, f"❌ ရောင်းရန်စာရင်းထဲတွင် '{item_name}' ကို မတွေ့ပါ။")
        return
        
    db.numbers.delete_one({'phone_number': item_name, 'status': 'AVAILABLE'})
    bot.send_message(message.chat.id, f"✅ '{item_name}' ကို အောင်မြင်စွာ ဖျက်လိုက်ပါပြီ။")

@bot.callback_query_handler(func=lambda call: call.data == "admin_db_status")
def callback_admin_backup(call):
    if call.from_user.id != ADMIN_ID: return
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "✅ **Database Status**\n\nယခုအခါ MongoDB Cloud (Atlas) ကို ပြောင်းလဲအသုံးပြုထားသောကြောင့် Data ပျက်စီးမည်ကို စိုးရိမ်ရန်မလိုတော့ပါ။ Backup ကို Cloud ပေါ်တွင် အလိုအလျောက် သိမ်းဆည်းပေးထားပါသည်။", parse_mode="Markdown")

@bot.message_handler(commands=['broadcast'])
def admin_broadcast(message):
    if message.from_user.id != ADMIN_ID: return
    
    if message.reply_to_message:
        bot.send_message(message.chat.id, "⏳ Broadcast ပို့နေပါသည် ခဏစောင့်ပါ...")
        succ = broadcast_to_users(original_message=message.reply_to_message)
        bot.send_message(message.chat.id, f"✅ လူ {succ} ဦးထံ အောင်မြင်စွာ ပို့ပြီးပါပြီ။")
        return
        
    txt = message.text.replace("/broadcast", "").strip()
    if not txt:
        bot.send_message(message.chat.id, "❌ ဥပမာ - စာရေးပြီးပို့လိုလျှင် `/broadcast မင်္ဂလာပါ` ဟုရိုက်ပါ။ (သို့မဟုတ်) ဓာတ်ပုံကို Reply ပြန်ပြီး `/broadcast` ဟုရိုက်ပါ။", parse_mode="Markdown")
        return
        
    bot.send_message(message.chat.id, "⏳ Broadcast ပို့နေပါသည် ခဏစောင့်ပါ...")
    succ = broadcast_to_users(text=txt)
    bot.send_message(message.chat.id, f"✅ လူ {succ} ဦးထံ အောင်မြင်စွာ ပို့ပြီးပါပြီ။")

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
        
        db.numbers.insert_one({
            'phone_number': phone,
            'operator': op,
            'price': price,
            'num_type': ntype,
            'status': 'AVAILABLE',
            'digital_info': ''
        })
            
        bot.send_message(message.chat.id, f"✅ ဖုန်းနံပါတ် {phone} ({op}) ထည့်ပြီးပါပြီ။ 📢 User အားလုံးနှင့် Channel သို့ အကြောင်းကြားစာ Auto ပို့ပေးနေပါသည်။")
        
        alert_msg = f"🌟 **ပစ္စည်းအသစ် ရောက်ရှိပါပြီ** 🌟\n\n📱 **နံပါတ်:** `{phone}`\n📡 **Operator:** {op}\n💰 **ဈေးနှုန်း:** {price:,.0f} ကျပ်\n✨ **အမျိုးအစား:** {ntype}\n\n👉 ယခုပဲ Bot ထဲတွင် ဝင်ရောက်ဝယ်ယူနိုင်ပါပြီ။"
        broadcast_to_users(text=alert_msg)
        
        try:
            bot_info = bot.get_me()
            channel_markup = types.InlineKeyboardMarkup()
            channel_markup.add(types.InlineKeyboardButton("🛒 Bot တွင် သွားရောက်ဝယ်ယူရန်", url=f"https://t.me/{bot_info.username}"))
            bot.send_message(CHANNEL_USERNAME, alert_msg, reply_markup=channel_markup, parse_mode="Markdown")
        except Exception as e:
            bot.send_message(message.chat.id, f"⚠️ Channel သို့ Post တင်ရာတွင် အမှားဖြစ်နေပါသည် (Bot ကို Channel Admin ပေးထားရန်လိုပါသည်): {e}")
        
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
            
        db.numbers.insert_one({
            'phone_number': acc_name,
            'operator': platform,
            'price': price,
            'num_type': ntype,
            'status': 'AVAILABLE',
            'digital_info': digital_info
        })
            
        bot.send_message(message.chat.id, f"✅ Digital Acc ('{acc_name}' - {mode}) အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ။ 📢 User များနှင့် Channel သို့ Auto ပို့နေပါသည်။")
        
        alert_msg = f"🎮 **Digital Account အသစ် ရောက်ရှိပါပြီ** 🎮\n\n📌 **အမည်:** {acc_name}\n🌐 **Platform:** {platform}\n💰 **ဈေးနှုန်း:** {price:,.0f} ကျပ်\n\n👉 ယခုပဲ Bot ထဲတွင် ဝင်ရောက်ဝယ်ယူနိုင်ပါပြီ။"
        broadcast_to_users(text=alert_msg)
        
        try:
            bot_info = bot.get_me()
            channel_markup = types.InlineKeyboardMarkup()
            channel_markup.add(types.InlineKeyboardButton("🛒 Bot တွင် သွားရောက်ဝယ်ယူရန်", url=f"https://t.me/{bot_info.username}"))
            bot.send_message(CHANNEL_USERNAME, alert_msg, reply_markup=channel_markup, parse_mode="Markdown")
        except Exception as e:
            bot.send_message(message.chat.id, f"⚠️ Channel သို့ Post တင်ရာတွင် အမှားဖြစ်နေပါသည်: {e}")
        
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Error: " + str(e))

# ==========================================
# 🛒 USER FEATURES (Search & Orders)
# ==========================================
@bot.message_handler(func=lambda m: m.text == "🔍 နံပါတ်ရှာဖွေမည်")
@require_channel_join
def prompt_search(message):
    msg = bot.send_message(message.chat.id, "🔍 ရှာဖွေလိုသော ဖုန်းနံပါတ် (သို့မဟုတ်) ဂဏန်းအချို့ကို ရိုက်ထည့်ပါ (ဥပမာ - `999` သို့မဟုတ် `094`):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, perform_search)

def perform_search(message):
    query = message.text.strip()
    if query in ["✨ နံပါတ်လှများကြည့်မည်", "🍀 Lucky Phone ကြည့်မည်", "📡 Operator အလိုက်ကြည့်မည်", "🎮 Digital Acc များ", "📞 ဆိုင်နှင့် ဆက်သွယ်ရန်"]:
        bot.send_message(message.chat.id, "ရှာဖွေခြင်း ပယ်ဖျက်လိုက်ပါသည်။")
        return
        
    rows = list(db.numbers.find({
        'status': 'AVAILABLE',
        'phone_number': {'$regex': query, '$options': 'i'}
    }).limit(16))
        
    if not rows:
        bot.send_message(message.chat.id, f"❌ '{query}' နှင့် ကိုက်ညီသော နံပါတ် မတွေ့ရှိပါ။", reply_markup=main_menu(message.from_user.id))
        return
        
    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows[:15]:
        markup.add(types.InlineKeyboardButton(f"{r['phone_number']} - {r['price']:,.0f} ကျပ်", callback_data="selectitem_" + str(r['_id'])))
        
    text = f"🔍 **ရှာဖွေမှုရလဒ်:** '{query}' နှင့် ကိုက်ညီသော နံပါတ် အချို့ တွေ့ရှိပါသည်။"
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🛒 ကျွန်ုပ်၏ အော်ဒါများ")
@require_channel_join
def my_order_history(message):
    uid = message.from_user.id
    rows = list(db.orders.find({'user_id': uid}).sort('_id', -1).limit(5))
        
    if not rows:
        bot.send_message(message.chat.id, "📭 လူကြီးမင်း ဝယ်ယူထားသော မှတ်တမ်း မရှိသေးပါ။")
        return
        
    text = "🛒 **လူကြီးမင်း၏ နောက်ဆုံး ဝယ်ယူမှုများ:**\n\n"
    for r in rows:
        status_mm = "✅ ပြီးစီး" if r['status'] == "COMPLETED" else ("❌ ပယ်ဖျက်" if r['status'] == "CANCELLED" else "⏳ စောင့်ဆိုင်းဆဲ")
        text += f"📦 #ORD-{r['order_id']:03d}\n🛍 **ပစ္စည်း:** `{r['chosen_number']}`\n💰 **ကျသင့်ငွေ:** {r['price']:,.0f} ကျပ်\n📊 **အခြေအနေ:** {status_mm}\n📅 {r['date'].strftime('%Y-%m-%d')}\n────────────────\n"
        
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

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
    auto_pipeline = [
        {'$match': {'num_type': 'DIGITAL_AUTO', 'status': 'AVAILABLE'}},
        {'$group': {
            '_id': '$phone_number',
            'item_id': {'$first': '$_id'},
            'operator': {'$first': '$operator'},
            'price': {'$max': '$price'},
            'stock': {'$sum': 1}
        }}
    ]
    auto_items = list(db.numbers.aggregate(auto_pipeline))
    manual_items = list(db.numbers.find({'num_type': 'DIGITAL_MANUAL', 'status': 'AVAILABLE'}))
    
    combined = []
    for a in auto_items:
        combined.append({'id': str(a['item_id']), 'name': a['_id'], 'operator': a['operator'], 'price': a['price'], 'stock': a['stock']})
    for m in manual_items:
        combined.append({'id': str(m['_id']), 'name': m['phone_number'], 'operator': m['operator'], 'price': m['price'], 'stock': 1})
        
    if not combined:
        if is_edit: bot.edit_message_text("📭 စာရင်း မရှိသေးပါ။", chat_id, message_id)
        else: bot.send_message(chat_id, "📭 စာရင်း မရှိသေးပါ။")
        return
        
    combined.sort(key=lambda x: x['price'])
    tpages = math.ceil(len(combined) / ITEMS_PER_PAGE)
    paged_rows = combined[page * ITEMS_PER_PAGE : (page + 1) * ITEMS_PER_PAGE]

    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in paged_rows:
        if r['stock'] > 1: btn_text = f"🎮 {r['name']} ( Stock: {r['stock']} ခု ) - {r['price']:,.0f} Ks"
        else: btn_text = f"🎮 {r['name']} ({r['operator']}) - {r['price']:,.0f} Ks"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data="selectitem_" + r['id']))

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
    pipeline = [
        {'$match': {'num_type': n_type, 'status': 'AVAILABLE'}},
        {'$group': {
            '_id': '$phone_number',
            'item_id': {'$first': '$_id'},
            'price': {'$max': '$price'}
        }},
        {'$sort': {'price': 1}},         {'$skip': page * ITEMS_PER_PAGE},
        {'$limit': ITEMS_PER_PAGE}
    ]
    rows = list(db.numbers.aggregate(pipeline))
    tot = len(db.numbers.distinct('phone_number', {'num_type': n_type, 'status': 'AVAILABLE'}))
    
    if tot == 0:
        if is_edit: bot.edit_message_text("📭 စာရင်း မရှိသေးပါ။", chat_id, message_id)
        else: bot.send_message(chat_id, "📭 စာရင်း မရှိသေးပါ။")
        return
        
    tpages = math.ceil(tot / ITEMS_PER_PAGE)
    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        markup.add(types.InlineKeyboardButton(f"📱 {r['_id']} - {r['price']:,.0f} Ks", callback_data="selectitem_" + str(r['item_id'])))

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
    pipeline = [
        {'$match': {'operator': op, 'status': 'AVAILABLE'}},
        {'$group': {'_id': '$phone_number', 'item_id': {'$first': '$_id'}, 'price': {'$max': '$price'}}},
        {'$sort': {'price': 1}},         {'$skip': page * ITEMS_PER_PAGE},
        {'$limit': ITEMS_PER_PAGE}
    ]
    rows = list(db.numbers.aggregate(pipeline))
    tot = len(db.numbers.distinct('phone_number', {'operator': op, 'status': 'AVAILABLE'}))
    
    if tot == 0:
        if is_edit: bot.edit_message_text("📭 စာရင်း မရှိသေးပါ။", chat_id, message_id)
        else: bot.send_message(chat_id, "📭 စာရင်း မရှိသေးပါ။")
        return
            
    tpages = math.ceil(tot / ITEMS_PER_PAGE)
    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        markup.add(types.InlineKeyboardButton(f"📱 {r['_id']} - {r['price']:,.0f} Ks", callback_data="selectitem_" + str(r['item_id'])))

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

@bot.callback_query_handler(func=lambda call: call.data.startswith("selectitem_"))
def process_buy(call):
    bot.answer_callback_query(call.id)
    nid_str = call.data.split("_")[1]
    
    item = db.numbers.find_one({'_id': ObjectId(nid_str)})
        
    if not item or (item['status'] == 'SOLD' and item['num_type'] not in ['DIGITAL_AUTO', 'DIGITAL_MANUAL']):
        bot.send_message(call.message.chat.id, "⚠️ ဤပစ္စည်း မရှိတော့ပါ။")
        return
        
    if item['num_type'] == 'DIGITAL_AUTO':
        actual_item = db.numbers.find_one({'phone_number': item['phone_number'], 'num_type': 'DIGITAL_AUTO', 'status': 'AVAILABLE'})
        if not actual_item:
            bot.send_message(call.message.chat.id, "⚠️ ဤပစ္စည်း Stock ကုန်သွားပါပြီ။")
            return
        nid_str = str(actual_item['_id'])
        phone_txt = actual_item['phone_number']
        price = actual_item['price']
    else:
        phone_txt = item['phone_number']
        price = item['price']
        
    ntype = item['num_type']
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if ntype == "DIGITAL_AUTO":
        markup.add(
            types.InlineKeyboardButton("📤 SS ပို့မည်", callback_data="prompt_digi_ss_" + nid_str),
            types.InlineKeyboardButton("❌ မဝယ်တော့ပါ", callback_data="cancel_buy_" + nid_str)
        )
        txt = f"🎮 **ရွေးချယ်ထားသော အကောင့်:** {phone_txt}\n💰 **ကျသင့်ငွေ:** {price:,.0f} ကျပ်\n\n" \
              f"💳 **ငွေလွှဲရန်:**\nWave: `09 792 654 163` (Si Thu Aung)\nKpay: `09 79 50 96 484` (Si Thu Aung)"
        try: bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except: bot.send_message(call.message.chat.id, txt, reply_markup=markup, parse_mode="Markdown")
        
    elif ntype == "DIGITAL_MANUAL":
        markup.add(
            types.InlineKeyboardButton("✅ သေချာပါသည် ဝယ်ယူမည်", callback_data="confdigi_manual_" + nid_str),
            types.InlineKeyboardButton("❌ မဝယ်တော့ပါ", callback_data="cancel_buy_" + nid_str)
        )
        txt = f"🎮 **ရွေးချယ်ထားသော အကောင့်:** {phone_txt}\n💰 **ကျသင့်ငွေ:** {price:,.0f} ကျပ်\n\n⚠️ Admin ကိုယ်တိုင် ဆောင်ရွက်ပေးရမည့် အမျိုးအစား ဖြစ်ပါသည်။"
        try: bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except: bot.send_message(call.message.chat.id, txt, reply_markup=markup, parse_mode="Markdown")
        
    else:
        markup.add(
            types.InlineKeyboardButton("❌ မဝယ်တော့ပါ", callback_data="cancel_buy_" + nid_str),
            types.InlineKeyboardButton("✅ ဝယ်ယူမည်", callback_data="confirm_buy_phone_" + nid_str)
        )
        txt = f"🎯 ရွေးချယ်ထားသောပစ္စည်း: {phone_txt}\n💰 ဈေးနှုန်း: {price:,.0f} ကျပ်\n\n" \
              f"⚠️ **Deli ခ 4,000 ကို ကြိုတင်လွှဲပေးရမည် ဖြစ်ပါသည်။**"
        try: bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except: bot.send_message(call.message.chat.id, txt, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_buy_phone_"))
def confirm_buy_phone_action(call):
    bot.answer_callback_query(call.id)
    nid = call.data.split("_")[3]
    msg = bot.send_message(call.message.chat.id, "📝 ကျေးဇူးပြု၍ သင့်၏ **နာမည်၊ ဖုန်းနံပါတ်၊ နှင့် လိပ်စာ** အတိအကျကို ရိုက်ထည့်ပေးပါ -")
    bot.register_next_step_handler(msg, receive_delivery_address, nid)

def receive_delivery_address(message, nid):
    if message.text in ["✨ နံပါတ်လှများကြည့်မည်", "🍀 Lucky Phone ကြည့်မည်", "📡 Operator အလိုက်ကြည့်မည်", "🎮 Digital Acc များ", "📞 ဆိုင်နှင့် ဆက်သွယ်ရန်", "👑 Admin Panel"]:
        bot.send_message(message.chat.id, "❌ ပယ်ဖျက်လိုက်ပါသည်။")
        return
    uid = message.from_user.id
    pending_order_address[uid] = message.text
    
    txt = f"💳 **ငွေလွှဲရန် အချက်အလက်များ:**\n\n" \
          f"Wave: `09 792 654 163` (Si Thu Aung)\n" \
          f"Kpay: `09 79 50 96 484` (Si Thu Aung)\n\n" \
          f"ကျေးဇူးပြု၍ ငွေလွှဲပြီးပါက အောက်ပါခလုတ်ကို နှိပ်၍ Screenshot (SS) ပုံ ပို့ပေးပါ။"
          
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📤 SS ပို့မည်", callback_data="send_order_ss_" + nid))
    bot.send_message(message.chat.id, txt, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("send_order_ss_"))
def send_order_ss_prompt(call):
    bot.answer_callback_query(call.id)
    nid = call.data.split("_")[3]
    msg = bot.send_message(call.message.chat.id, "🖼️ ကျေးဇူးပြု၍ ငွေလွှဲထားသော **Screenshot (SS) ပုံ** ကို ပို့ပေးပါ။")
    bot.register_next_step_handler(msg, receive_regular_order_ss, nid)

def receive_regular_order_ss(message, nid):
    if message.content_type != 'photo':
        msg = bot.send_message(message.chat.id, "❌ ကျေးဇူးပြု၍ ပုံ (Photo) သာ ပို့ပေးပါ။ ထပ်မံပို့ပေးပါ:")
        bot.register_next_step_handler(msg, receive_regular_order_ss, nid)
        return
        
    photo_id = message.photo[-1].file_id
    uid = message.from_user.id
    fname = message.from_user.first_name
    address = pending_order_address.get(uid, "လိပ်စာ မပါရှိပါ")
    
    item = db.numbers.find_one({'_id': ObjectId(nid)})
    if not item:
        bot.send_message(message.chat.id, "❌ ဤပစ္စည်း မရှိတော့ပါ။")
        return
        
    phone = item['phone_number']
    price = item['price']
        
    db.numbers.update_one({'_id': ObjectId(nid)}, {'$set': {'status': 'SOLD'}})
    oid = get_next_order_id()
    
    db.orders.insert_one({
        'order_id': oid, 'user_id': uid, 'customer_name': fname, 'chosen_number': phone,
        'price': price, 'contact_info': address, 'ref_id': ObjectId(nid),
        'status': 'PENDING', 'date': datetime.now()
    })
        
    success_txt = f"✅ **အော်ဒါတင်ခြင်း အောင်မြင်ပါသည်။** (#ORD-{oid:03d})\n\n" \
                  f"💬 ကျေးဇူးတင်ပါသည်။ Admin မှ စစ်ဆေးပြီး အမြန်ဆုံး ပို့ဆောင်ပေးပါမည်။"
    bot.send_message(message.chat.id, success_txt, parse_mode="Markdown")
    
    try:
        user_link = f"[{fname}](tg://user?id={uid})"
        admin_msg = f"🔔 **အော်ဒါသစ်:** #ORD-{oid:03d}\n👤 ဝယ်သူ: {user_link}\n🛍 မှာယူသည့်အရာ: {phone}\n💰 ဈေးနှုန်း: {price:,.0f} ကျပ်\n📍 လိပ်စာ: {address}"
        admin_markup = types.InlineKeyboardMarkup(row_width=1)
        admin_markup.add(
            types.InlineKeyboardButton("✅ ပြီးစီးပါပြီ (Completed)", callback_data=f"admin_comp_ord_{oid}"),
            types.InlineKeyboardButton("❌ ဤအော်ဒါကို Cancel မည်", callback_data=f"admin_cancel_ord_{oid}")
        )
        bot.send_photo(ADMIN_ID, photo_id, caption=admin_msg, reply_markup=admin_markup, parse_mode="Markdown")
    except Exception: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("confdigi_manual_"))
def confirm_digital_manual_buy(call):
    bot.answer_callback_query(call.id)
    nid = call.data.split("_")[2]
    uid = call.from_user.id
    fname = call.from_user.first_name
    
    item = db.numbers.find_one({'_id': ObjectId(nid)})
    if not item: return
    phone = item['phone_number']
    price = item['price']
        
    oid = get_next_order_id()
    db.orders.insert_one({
        'order_id': oid, 'user_id': uid, 'customer_name': fname, 'chosen_number': phone,
        'price': price, 'contact_info': "Digital Manual", 'ref_id': ObjectId(nid),
        'status': 'PENDING', 'date': datetime.now()
    })
        
    txt = f"✅ **အော်ဒါ ရွေးချယ်မှု အောင်မြင်ပါသည်။** (#ORD-{oid:03d})\n\n" \
          f"🎮 **အကောင့်/ပစ္စည်း:** {phone}\n💰 **ကျသင့်ငွေ:** {price:,.0f} ကျပ်\n\n" \
          f"💬 **ငွေပေးချေရန်နှင့် ဝန်ဆောင်မှုရယူရန်အတွက် -**\nကျေးဇူးပြု၍ Admin 👉 @orange310199 သို့ ငွေလွှဲ SS နှင့်အတူ ယခုပဲ Message သွားပို့ပေးပါခင်ဗျာ။"
    
    bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    
    try:
        user_link = f"[{fname}](tg://user?id={uid})"
        admin_msg = f"🔔 **Digital (MANUAL) အော်ဒါသစ်:** #ORD-{oid:03d}\n👤 ဝယ်သူ: {user_link}\n🛍 မှာယူသည့်အရာ: {phone}\n💰 ဈေးနှုန်း: {price:,.0f} ကျပ်"
        admin_markup = types.InlineKeyboardMarkup(row_width=1)
        admin_markup.add(
            types.InlineKeyboardButton("✅ ပြီးစီးပါပြီ (Completed)", callback_data=f"admin_comp_ord_{oid}"),
            types.InlineKeyboardButton("❌ ဤအော်ဒါကို Cancel မည်", callback_data=f"admin_cancel_ord_{oid}")
        )
        bot.send_message(ADMIN_ID, admin_msg, reply_markup=admin_markup, parse_mode="Markdown")
    except Exception: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("prompt_digi_ss_"))
def prompt_digi_ss(call):
    bot.answer_callback_query(call.id)
    nid = call.data.split("_")[3]
    msg = bot.send_message(call.message.chat.id, "🖼️ ကျေးဇူးပြု၍ ငွေလွှဲထားသော Screenshot (SS) ပုံ ကို ပို့ပေးပါ။")
    bot.register_next_step_handler(msg, receive_digi_order_ss, nid)

def receive_digi_order_ss(message, nid):
    if message.content_type != 'photo':
        msg = bot.send_message(message.chat.id, "❌ ကျေးဇူးပြု၍ ပုံ (Photo) သာ ပို့ပေးပါ။ ကျေးဇူးပြု၍ SS ပုံကို ထပ်မံပို့ပေးပါ:")
        bot.register_next_step_handler(msg, receive_digi_order_ss, nid)
        return
        
    photo_id = message.photo[-1].file_id
    uid = message.from_user.id
    fname = message.from_user.first_name
    
    item = db.numbers.find_one({'_id': ObjectId(nid)})
    if not item:
        bot.send_message(message.chat.id, "❌ ဤပစ္စည်း မရှိတော့ပါ။")
        return
        
    user_link = f"[{fname}](tg://user?id={uid})"
    admin_txt = f"🎮 **Digital အော်ဒါ (ငွေလွှဲ SS ပို့ထားသည်)**\n\n👤 ဝယ်သူ: {user_link}\n🆔 User ID: `{uid}`\n🛍 အကောင့်: {item['phone_number']}\n💰 ဈေးနှုန်း: {item['price']:,.0f} ကျပ်"
    
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
    nid = parts[3]
    user_id = int(parts[4])
    
    item = db.numbers.find_one({'_id': ObjectId(nid)})
    if not item:
        bot.answer_callback_query(call.id, "ပစ္စည်း မရှိတော့ပါ။", show_alert=True)
        return
        
    db.numbers.update_one({'_id': ObjectId(nid)}, {'$set': {'status': 'SOLD'}})
    oid = get_next_order_id()
    db.orders.insert_one({
        'order_id': oid, 'user_id': user_id, 'customer_name': "Customer",
        'chosen_number': item['phone_number'], 'price': item['price'],
        'contact_info': "Digital Auto Delivery", 'ref_id': ObjectId(nid),
        'status': 'COMPLETED', 'date': datetime.now()
    })
        
    bot.answer_callback_query(call.id, "အော်ဒါကို ခွင့်ပြုပြီး အကောင့်ပို့လိုက်ပါပြီ။")
    bot.edit_message_caption(caption=call.message.caption + "\n\n✅ **[ခွင့်ပြုပြီး အကောင့်ပို့ပြီးပါပြီ]**", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
    
    try:
        txt = f"🎉 **ဝယ်ယူမှု အောင်မြင်ပါသည်။** (#ORD-{oid:03d})\n\n" \
              f"🎮 **အကောင့်:** {item['phone_number']}\n" \
              f"🔑 **အချက်အလက် (Account Info):**\n`{item.get('digital_info','')}`\n\n" \
              f"ကျေးဇူးတင်ပါတယ်။ အချက်အလက်များကို Copy ကူးယူနိုင်ပါပြီ။"
        bot.send_message(user_id, txt, parse_mode="Markdown")
    except Exception: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_rej_digi_"))
def admin_reject_digital_order(call):
    if call.from_user.id != ADMIN_ID: return
    user_id = int(call.data.split("_")[4])
    
    bot.answer_callback_query(call.id, "အော်ဒါကို ပယ်ချလိုက်ပါပြီ။")
    bot.edit_message_caption(caption=call.message.caption + "\n\n❌ **[ပယ်ချလိုက်ပါပြီ]**", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
    
    try:
        bot.send_message(user_id, "⚠️ တောင်းပန်ပါတယ်၊ သင်တင်ပြလာသော ငွေလွှဲပြေစာ (SS) မမှန်ကန်ပါသဖြင့် အော်ဒါကို ပယ်ချလိုက်ပါသည်။")
    except Exception: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_buy_"))
def user_cancel_buy(call):
    bot.answer_callback_query(call.id)
    bot.clear_step_handler_by_chat_id(call.message.chat.id)
    
    nid_str = call.data.replace("cancel_buy_", "")
    try:
        item = db.numbers.find_one({'_id': ObjectId(nid_str)})
        if item:
            ntype = item.get('num_type')
            op = item.get('operator')
            if ntype in ["PRO", "LUCKY"]:
                send_paginated_numbers(call.message.chat.id, ntype, 0, is_edit=True, message_id=call.message.message_id)
                return
            elif ntype in ["DIGITAL_AUTO", "DIGITAL_MANUAL"]:
                send_paginated_digital(call.message.chat.id, 0, is_edit=True, message_id=call.message.message_id)
                return
            else:
                send_paginated_operators(call.message.chat.id, op, 0, is_edit=True, message_id=call.message.message_id)
                return
    except:
        pass
                    
    bot.edit_message_text("ဝယ်ယူမှုကို ပယ်ဖျက်လိုက်ပါပြီ။", call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "✨ *VIP Shop Bot မှ ကြိုဆိုပါတယ်။*", reply_markup=main_menu(call.from_user.id), parse_mode="Markdown")

# 🚀 Bot စတင် Run ရန်
print("Bot is running...")
if __name__ == "__main__":
    # ရုတ်တရက်ရပ်သွားခြင်းကိုကာကွယ်ရန် infinity_polling ကိုပြောင်းသုံးထားပါသည်
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

