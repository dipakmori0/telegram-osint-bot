import sqlite3
import re
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import Forbidden, BadRequest

# ===== CONFIG =====
BOT_TOKEN = "8277485140:AAERBu7ErxHReWZxcYklneU1wEXY--I_32c"
CHANNEL_ID = "@taskblixosint"
API_KEY = "7658050410:qQ88TxXl"
API_URL = "https://leakosintapi.com/"
OWNER_ID = 8270660057  # Admin/Owner ID

# ===== DATABASE =====
conn = sqlite3.connect("bot.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    credits INTEGER DEFAULT -1,
    banned INTEGER DEFAULT 0
);
""")
c.execute("""
CREATE TABLE IF NOT EXISTS logs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT,
    created_at TEXT
);
""")
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
    from datetime import datetime
    now = datetime.utcnow().isoformat()
    c.execute("INSERT INTO logs(user_id, action, created_at) VALUES (?, ?, ?)", (user_id, action, now))
    conn.commit()

def is_admin(user_id):
    return user_id == OWNER_ID

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Search", callback_data="search"),
         InlineKeyboardButton("👑 Owner", callback_data="owner")],
        [InlineKeyboardButton("ℹ Help", callback_data="help"),
         InlineKeyboardButton("⚖ Legal", callback_data="legal")]
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
                                key_lower = key.lower()
                                if key_lower.startswith("phone"):
                                    result_text += f"📞 Phone: {value}\n"
                                elif key_lower.startswith("address"):
                                    result_text += f"🏘️ Address: {value}\n"
                                elif key_lower in ["fullname", "full_name"]:
                                    result_text += f"👤 Full Name: {value}\n"
                                elif key_lower in ["fathername", "father_name"]:
                                    result_text += f"👨 Father: {value}\n"
                                elif key_lower in ["docnumber", "document"]:
                                    result_text += f"🃏 Document: {value}\n"
                                elif key_lower in ["login", "username", "nick"]:
                                    result_text += f"🏷️ Login: {value}\n"
                                elif key_lower == "region":
                                    result_text += f"🗺️ Region: {value}\n"
                        result_text += "\n"
        else:
            result_text += str(data)
    except Exception as e:
        result_text = f"⚠ API Error: {e}"

    result_text += "\n💳 Credits: Unlimited\n⚠ For educational purposes only"
    return result_text


# ===== COMMAND HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    uname = update.effective_user.username or update.effective_user.first_name
    add_user(uid, uname)
    log_action(uid, "start")

    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, uid)
        if member.status not in ["member", "administrator", "creator"]:
            kb = [[InlineKeyboardButton("🚀 Join Channel", url=f"https://t.me/{CHANNEL_ID[1:]}")]]
            await update.message.reply_text("📢 Please join our channel first!", reply_markup=InlineKeyboardMarkup(kb))
            return
    except (Forbidden, BadRequest):
        pass

    msg = (
        f"👋 Hello {uname}!\n\n"
        "📌 How to use:\n"
        "• Send a number/email/name directly: `919023370810`\n"
        "• Or use: `/num 919023370810`\n"
        "• Check credits: /credits\n\n"
        "⚡ Unlimited credits"
    )
    await update.message.reply_text(msg, reply_markup=main_menu_keyboard())


async def credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💳 You have Unlimited credits.")


async def num_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: /num <number/email/name>")
        return
    query = " ".join(context.args)
    log_action(update.effective_user.id, f"num {query}")
    await update.message.reply_text(fetch_info(query))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    # Numbers, emails, names
    if re.fullmatch(r"[0-9+]{10,13}", text) or re.fullmatch(r".+@.+\..+", text) or len(text) > 2:
        log_action(update.effective_user.id, f"direct {text}")
        await update.message.reply_text(fetch_info(text))
    else:
        await update.message.reply_text("❌ Invalid input. Send a number/email/name.")


# ===== INLINE BUTTON HANDLER =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "owner":
        kb = [[InlineKeyboardButton("↩ Back", callback_data="mainmenu")]]
        await query.edit_message_text("👑 Bot Owner:\n👉 [@TASKBLIX](https://t.me/TASKBLIX)", reply_markup=InlineKeyboardMarkup(kb))
    elif query.data == "help":
        kb = [[InlineKeyboardButton("↩ Back", callback_data="mainmenu")]]
        await query.edit_message_text(
            "📖 Help:\n• Send number/email/name to get info\n• /credits → Check credits",
            reply_markup=InlineKeyboardMarkup(kb)
        )
    elif query.data == "legal":
        kb = [[InlineKeyboardButton("↩ Back", callback_data="mainmenu")]]
        await query.edit_message_text(
            "⚖ Legal Disclaimer\nFor educational purposes only",
            reply_markup=InlineKeyboardMarkup(kb)
        )
    elif query.data == "search":
        kb = [[InlineKeyboardButton("↩ Back", callback_data="mainmenu")]]
        await query.edit_message_text("🔍 Send number/email/name directly or use `/num <query>`", reply_markup=InlineKeyboardMarkup(kb))
    elif query.data == "mainmenu":
        await query.edit_message_text("👋 Choose an option:", reply_markup=main_menu_keyboard())


# ===== ADMIN COMMANDS =====
async def add_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("❌ You are not authorized.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: /addcredit <user_id> <amount>")
        return
    try:
        target = int(context.args[0])
        amount = int(context.args[1])
        c.execute("UPDATE users SET credits = credits + ? WHERE user_id=?", (amount, target))
        conn.commit()
        log_action(uid, f"addcredit {amount} to {target}")
        await update.message.reply_text(f"✅ Added {amount} credits to {target}")
    except Exception as e:
        await update.message.reply_text(f"⚠ Error: {e}")


# ===== RUN BOT =====
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("credits", credits))
    app.add_handler(CommandHandler("num", num_command))
    app.add_handler(CommandHandler("addcredit", add_credit))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
