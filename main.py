import sqlite3
import requests
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# ===== CONFIG =====
BOT_TOKEN = "8277485140:AAERBu7ErxHReWZxcYklneU1wEXY--I_32c"
CHANNEL_A_ID = -1002851939876
CHANNEL_A_LINK = "https://t.me/+eB_J_ExnQT0wZDU9"
CHANNEL_B_ID = -1002321550721
CHANNEL_B_LINK = "https://t.me/taskblixosint"
API_KEY = "7658050410:qQ88TxXl"
API_URL = "https://leakosintapi.com/"
OWNER_ID = 8270660057

# ===== DATABASE =====
conn = sqlite3.connect("bot.db", check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                credits INTEGER DEFAULT -1
            )""")
conn.commit()

# ===== BOT INIT =====
bot = Bot(BOT_TOKEN)
app = Flask(__name__)

# ===== HELPERS =====
def add_user(user_id: int, username: str):
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users(user_id, username, credits) VALUES(?, ?, ?)", (user_id, username, -1))
        conn.commit()

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Search", callback_data="search"),
         InlineKeyboardButton("👑 Owner", callback_data="owner")],
        [InlineKeyboardButton("ℹ Help", callback_data="help"),
         InlineKeyboardButton("⚖ Legal", callback_data="legal")]
    ])

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    add_user(user_id, username)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel 1", url=CHANNEL_A_LINK)],
        [InlineKeyboardButton("📣 Join Channel 2", url=CHANNEL_B_LINK)]
    ])
    await update.message.reply_text(
        f"👋 Hello {username}!\n💳 You have Unlimited credits\n\n"
        "Please join both channels first.",
        reply_markup=keyboard
    )
    await update.message.reply_text("👋 Choose an option:", reply_markup=main_menu_keyboard())

# ===== MENU BUTTON =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "owner":
        kb = [[InlineKeyboardButton("↩ Back", callback_data="mainmenu")]]
        await query.edit_message_text("👑 Bot Owner:\n👉 [@TASKBLIX](https://t.me/TASKBLIX)", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    elif query.data == "help":
        kb = [[InlineKeyboardButton("↩ Back", callback_data="mainmenu")]]
        await query.edit_message_text(
            "📖 Help Menu:\nUse /num <number/email/name> to search info.\nAdmin: /addcredit <userid> <amount>",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
        )
    elif query.data == "legal":
        kb = [[InlineKeyboardButton("↩ Back", callback_data="mainmenu")]]
        await query.edit_message_text(
            "⚖ Legal Disclaimer: For educational purposes only.",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
        )
    elif query.data == "search":
        kb = [[InlineKeyboardButton("↩ Back", callback_data="mainmenu")]]
        await query.edit_message_text(
            "🔍 Use direct number/email/name to search:\nExample: 919023370810",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
        )
    elif query.data == "mainmenu":
        await query.edit_message_text("👋 Choose an option:", reply_markup=main_menu_keyboard())

# ===== CREDITS =====
async def credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💳 You have Unlimited credits.")

# ===== NUM LOOKUP =====
async def num_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        res = requests.get(f"{API_URL}?number={query}", headers=headers, timeout=10)
        data = res.json()
        sim_info = data.get("sim", "N/A")
        operator = data.get("operator", "N/A")
        region = data.get("region", "N/A")
        response = f"📞 Number info for {query}:\n- SIM Info: {sim_info}\n- Operator: {operator}\n- Region: {region}"
    except Exception as e:
        response = f"❌ Failed: {str(e)}"
    await update.message.reply_text(response)

# ===== ADMIN =====
async def add_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ Not authorized")
        return
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Usage: /addcredit <userid> <amount>")
        return
    target, amount = int(args[0]), int(args[1])
    c.execute("UPDATE users SET credits = credits + ? WHERE user_id=?", (amount, target))
    conn.commit()
    await update.message.reply_text(f"✅ Added {amount} credits to {target}")

# ===== TELEGRAM WEBHOOK =====
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler

application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("credits", credits))
application.add_handler(CommandHandler("addcredit", add_credit))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, num_lookup))
application.add_handler(CallbackQueryHandler(button_handler))

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    application.bot.process_new_updates([update])
    return "OK", 200

# ===== RUN =====
if __name__ == "__main__":
    # Set webhook manually once:
    print("Set Telegram webhook using:")
    print(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url=https://<YOUR_RENDER_URL>/{BOT_TOKEN}")
