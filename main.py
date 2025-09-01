import sqlite3
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from flask import Flask, request
import os

# ===== CONFIG =====
BOT_TOKEN = "8277485140:AAERBu7ErxHReWZxcYklneU1wEXY--I_32c"
OWNER_ID = 8270660057

CHANNEL_A_ID = -1002851939876
CHANNEL_A_LINK = "https://t.me/+eB_J_ExnQT0wZDU9"

CHANNEL_B_ID = -1002321550721
CHANNEL_B_LINK = "https://t.me/taskblixosint"

API_KEY = "7658050410:qQ88TxXl"
API_URL = "https://leakosintapi.com/"

DB_PATH = "bot.db"

# ===== DATABASE =====
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    credits INTEGER DEFAULT -1,
    banned INTEGER DEFAULT 0
)""")
c.execute("""CREATE TABLE IF NOT EXISTS logs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT,
    created_at TEXT
)""")
conn.commit()

# ===== HELPERS =====
def add_user(user_id, username):
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, username, credits) VALUES (?, ?, ?)", (user_id, username, -1))
        conn.commit()
        return True
    return False

def log_action(user_id, action):
    now = datetime.utcnow().isoformat()
    c.execute("INSERT INTO logs(user_id, action, created_at) VALUES (?, ?, ?)", (user_id, action, now))
    conn.commit()

def is_admin(user_id):
    return user_id == OWNER_ID

def is_verified(user_id, bot):
    try:
        a = bot.get_chat_member(CHANNEL_A_ID, user_id)
        b = bot.get_chat_member(CHANNEL_B_ID, user_id)
        return a.status in ["member", "administrator", "creator"] and \
               b.status in ["member", "administrator", "creator"]
    except:
        return False

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Search", callback_data="search"),
         InlineKeyboardButton("👑 Owner", callback_data="owner")],
        [InlineKeyboardButton("ℹ Help", callback_data="help"),
         InlineKeyboardButton("⚖ Legal", callback_data="legal")]
    ])

def join_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel 1", url=CHANNEL_A_LINK)],
        [InlineKeyboardButton("📣 Join Channel 2", url=CHANNEL_B_LINK)],
        [InlineKeyboardButton("✅ I have joined", callback_data="verify")]
    ])

def fetch_info(query: str) -> str:
    try:
        payload = {"token": API_KEY, "request": query, "limit": 100, "lang": "en"}
        res = requests.post(API_URL, json=payload, timeout=30)
        data = res.json()
        result_text = f"🔍 Lookup result for {query}:\n\n"
        if "List" in data:
            for source, source_data in data["List"].items():
                result_text += f"📂 Source: {source}\n"
                if "Data" in source_data:
                    for entry in source_data["Data"]:
                        for key, value in entry.items():
                            if value:
                                k = key.lower()
                                if k.startswith("phone"):
                                    result_text += f"📞 Phone: {value}\n"
                                elif k.startswith("address"):
                                    result_text += f"🏘️ Address: {value}\n"
                                elif k in ["fullname","full_name"]:
                                    result_text += f"👤 Full Name: {value}\n"
                                elif k in ["fathername","father_name"]:
                                    result_text += f"👨 Father: {value}\n"
                                elif k in ["docnumber","document"]:
                                    result_text += f"🃏 Document: {value}\n"
                                elif k in ["login","username","nick"]:
                                    result_text += f"🏷️ Login: {value}\n"
                                elif k=="region":
                                    result_text += f"🗺️ Region: {value}\n"
                        result_text += "\n"
        else:
            result_text += str(data)
    except Exception as e:
        result_text = f"⚠ API Error: {e}"
    result_text += "\n💳 Credits: Unlimited\n⚠ For educational purposes only"
    return result_text

# ===== COMMANDS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    uname = update.effective_user.username or update.effective_user.first_name
    add_user(uid, uname)
    log_action(uid, "start")

    if not is_verified(uid, context.bot):
        await update.message.reply_text("🔒 Please join both channels first:", reply_markup=join_kb())
        return

    msg = (
        f"👋 Hello {uname}!\n\n"
        "📌 How to use:\n"
        "• Send a number/email/name directly, e.g., `919023370810`\n"
        "• Check credits: /credits\n"
        "• Admin commands for owner\n\n"
        "⚡ Unlimited credits"
    )
    await update.message.reply_text(msg, reply_markup=main_menu_keyboard())

async def credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💳 You have Unlimited credits.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    log_action(update.effective_user.id, f"direct {text}")
    await update.message.reply_text(fetch_info(text))

# ===== CALLBACK HANDLER =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    kb = [[InlineKeyboardButton("↩ Back", callback_data="mainmenu")]]
    if data=="owner":
        await query.edit_message_text("👑 Bot Owner: [@TASKBLIX](https://t.me/TASKBLIX)", reply_markup=InlineKeyboardMarkup(kb))
    elif data=="help":
        await query.edit_message_text("📖 Help:\nSend number/email/name to lookup", reply_markup=InlineKeyboardMarkup(kb))
    elif data=="legal":
        await query.edit_message_text("⚖ Legal Disclaimer\nFor educational purposes only", reply_markup=InlineKeyboardMarkup(kb))
    elif data=="search":
        await query.edit_message_text("🔍 Send number/email/name directly", reply_markup=InlineKeyboardMarkup(kb))
    elif data=="verify":
        if is_verified(query.from_user.id, context.bot):
            await query.edit_message_text("✅ Verified! You can now use the bot.")
        else:
            await query.answer("❌ Not verified. Join both channels.", show_alert=True)
    elif data=="mainmenu":
        await query.edit_message_text("👋 Choose an option:", reply_markup=main_menu_keyboard())

# ===== ADMIN =====
async def add_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("❌ Not authorized")
        return
    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: /addcredit <user_id> <amount>")
        return
    try:
        target = int(context.args[0])
        amount = int(context.args[1])
        c.execute("UPDATE users SET credits=credits+? WHERE user_id=?", (amount, target))
        conn.commit()
        log_action(uid, f"addcredit {amount} to {target}")
        await update.message.reply_text(f"✅ Added {amount} credits to {target}")
    except Exception as e:
        await update.message.reply_text(f"⚠ Error: {e}")

# ===== WEBHOOK RUN =====
def main():
    app = Flask(__name__)
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("credits", credits))
    bot_app.add_handler(CommandHandler("addcredit", add_credit))
    bot_app.add_handler(CallbackQueryHandler(button_handler))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    @app.route(f"/{BOT_TOKEN}", methods=["POST"])
    def webhook():
        from telegram import Update
        update = Update.de_json(request.get_json(force=True), bot_app.bot)
        bot_app.update_queue.put(update)
        return "ok"

    @app.route("/")
    def index():
        return "Bot is running..."

    url = os.environ.get("RENDER_EXTERNAL_URL")
    if url:
        bot_app.bot.set_webhook(f"{url}/{BOT_TOKEN}")

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

if __name__ == "__main__":
    main()
