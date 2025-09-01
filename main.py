import sqlite3
import requests
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import Forbidden, BadRequest

# ==== CONFIG ====
BOT_TOKEN = "8277485140:AAERBu7ErxHReWZxcYklneU1wEXY--I_32c"
CHANNEL_ID = "@taskblixosint"
API_KEY = "7658050410:qQ88TxXl"
API_URL = "https://leakosintapi.com/"
ADMINS = [8270660057]

# ==== DB Setup ====
conn = sqlite3.connect("bot.db", check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                credits INTEGER DEFAULT -1
            )""")
conn.commit()


# ==== Helper Functions ====
async def safe_send(update: Update, text: str, reply_markup=None):
    try:
        if update.message:
            await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    except Exception as e:
        print("Send error:", e)


def add_user(user_id: int, username: str):
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (user_id, username, credits) VALUES (?, ?, ?)",
                  (user_id, username, -1))
        conn.commit()
        return True
    return False


def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Search", callback_data="search"),
         InlineKeyboardButton("👑 Owner", callback_data="owner")],
        [InlineKeyboardButton("ℹ Help", callback_data="help"),
         InlineKeyboardButton("⚖ Legal", callback_data="legal")]
    ])


# ==== START COMMAND ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    new_user = add_user(user_id, username)

    if new_user:
        await safe_send(update, f"✅ Welcome {username}! You have Unlimited credits 🎁")
    else:
        await safe_send(update, f"✅ Welcome back {username}! You have Unlimited credits.")

    # Force join channel
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status not in ["member", "administrator", "creator"]:
            keyboard = [[InlineKeyboardButton("🚀 Join Channel", url=f"https://t.me/{CHANNEL_ID[1:]}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("📢 Please join our channel first!", reply_markup=reply_markup)
            return
    except (Forbidden, BadRequest):
        pass

    msg = (
        "👋 Choose an option or just send a number/email/name to lookup.\n\n"
        "📌 How to use:\n"
        "• Send a number directly: `919023370810`\n"
        "• Or use command: `/num 919023370810`\n"
        "• Check credits: /credits\n\n"
        "⚡ Unlimited credits."
    )
    await update.message.reply_text(msg, reply_markup=main_menu_keyboard())


# ==== MENU BUTTON HANDLER ====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "owner":
        keyboard = [[InlineKeyboardButton("↩ Back", callback_data="mainmenu")]]
        await query.edit_message_text(
            "👑 Bot Owner:\n👉 [@TASKBLIX](https://t.me/TASKBLIX)",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "help":
        keyboard = [[InlineKeyboardButton("↩ Back", callback_data="mainmenu")]]
        await query.edit_message_text(
            "📖 *Help Menu*\n\n"
            "• Send number/email/name → Get info\n"
            "• /credits → Check credits\n"
            "• Use main menu buttons for navigation.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "legal":
        keyboard = [[InlineKeyboardButton("↩ Back", callback_data="mainmenu")]]
        await query.edit_message_text(
            "⚖ *Legal Disclaimer*\n\n"
            "This bot is made *only for educational and research purposes*.\n"
            "❌ Illegal use prohibited.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "search":
        keyboard = [[InlineKeyboardButton("↩ Back", callback_data="mainmenu")]]
        await query.edit_message_text(
            "🔍 *Search Guide*\n\n"
            "Send a number/email/name directly or use `/num <query>`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "mainmenu":
        await query.edit_message_text("👋 Choose an option:", reply_markup=main_menu_keyboard())


# ==== CREDITS ====
async def credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_send(update, "💳 You have Unlimited credits.")


# ==== NUM LOOKUP ====
async def num_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await safe_send(update, "❌ Usage: /num <number/email/name>")
        return

    query = " ".join(context.args)
    await safe_send(update, fetch_info(query))


# ==== DIRECT MESSAGE HANDLER (numbers/emails/names) ====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if re.fullmatch(r"[0-9+]{10,13}", text) or re.fullmatch(r".+@.+\..+", text) or len(text) > 2:
        await safe_send(update, fetch_info(text))
    else:
        await safe_send(update, "❌ Invalid input. Send a number/email/name.")


# ==== API FETCH FUNCTION ====
def fetch_info(query: str) -> str:
    try:
        payload = {"token": API_KEY, "request": query, "limit": 100, "lang": "en"}
        response = requests.post(API_URL, json=payload, timeout=30)
        data = response.json()

        result_text = f"🔍 Lookup result for {query}:\n\n"
        if "List" in data:
            for source, source_data in data["List"].items():
                result_text += f"📂 Source: {source}\n"
                if "Data" in source_data:
                    for entry in source_data["Data"]:
                        for key, value in entry.items():
                            if value:
                                if key.lower().startswith("phone"):
                                    result_text += f"📞 Telephone: {value}\n"
                                elif key.lower().startswith("address"):
                                    result_text += f"🏘️ Address: {value}\n"
                                elif key.lower() in ["fullname", "full_name"]:
                                    result_text += f"👤 Full name: {value}\n"
                                elif key.lower() in ["fathername", "father_name"]:
                                    result_text += f"👨 Father: {value}\n"
                                elif key.lower() in ["docnumber", "document"]:
                                    result_text += f"🃏 Document: {value}\n"
                                elif key.lower() in ["login", "username", "nick"]:
                                    result_text += f"🏷️ Login: {value}\n"
                                elif key.lower() == "region":
                                    result_text += f"🗺️ Region: {value}\n"
                        result_text += "\n"
        else:
            result_text += str(data)

    except Exception as e:
        result_text = f"⚠ API Error: {e}"

    result_text += "\n💳 Credits: Unlimited"
    result_text += "\n⚠ For educational purposes only"
    return result_text


# ==== ADMIN ADD CREDIT ====
async def add_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        await safe_send(update, "❌ You are not authorized to use this command.")
        return

    if len(context.args) < 2:
        await safe_send(update, "❌ Usage: /addcredit <userid> <amount>")
        return

    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
        c.execute("UPDATE users SET credits = credits + ? WHERE user_id=?", (amount, target_id))
        conn.commit()
        await safe_send(update, f"✅ Added {amount} credits to user {target_id}.")
    except Exception as e:
        await safe_send(update, f"⚠️ Error: {e}")


# ==== MAIN FUNCTION ====
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("credits", credits))
    app.add_handler(CommandHandler("num", num_lookup))
    app.add_handler(CommandHandler("addcredit", add_credit))

    # Callback buttons
    app.add_handler(CallbackQueryHandler(button_handler))

    # Direct message handler
    app.add_handler
