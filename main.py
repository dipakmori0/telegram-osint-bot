import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ========== CONFIG ==========
BOT_TOKEN = "8277485140:AAERBu7ErxHReWZxcYklneU1wEXY--I_32c"  # <-- Tumhara Bot Token

# Group / Channel restrictions (agar required hai)
REQUIRED_GROUP_ID = -1002704011071
REQUIRED_CHANNEL_ID = -1002866215598

# API Config
LEAK_API_URL = "https://leakosintapi.com/"
LEAK_API_KEY = "7658050410:qQ88TxXl"   # <-- Ye API key hai

OWNER_ID = 7905118687
# ============================


# --------- START COMMAND ---------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = (
        f"👋 Hello {user.mention_html()}!\n"
        "✅ Welcome to the Info Lookup Bot\n\n"
        "📌 Commands:\n"
        "/num <number> → Get SIM/Operator info\n"
        "/help → Show help"
    )
    await update.message.reply_text(msg, parse_mode="HTML")


# --------- HELP COMMAND ---------
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🛠 Available Commands:\n"
        "/start → Welcome message\n"
        "/num <number> → Lookup number info\n"
        "/help → Show this message\n\n"
        "⚠️ Bot works only in specific group & channel."
    )
    await update.message.reply_text(msg)


# --------- NUM COMMAND ---------
async def num(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /num <phonenumber>")
        return

    number = context.args[0].strip()
    await update.message.reply_text(f"🔍 Fetching info for {number}...")

    try:
        headers = {"Authorization": f"Bearer {LEAK_API_KEY}"} if LEAK_API_KEY else {}
        params = {"number": number}
        res = requests.get(LEAK_API_URL, params=params, headers=headers, timeout=12)

        # 🟢 Debug print → Render logs me raw reply dikhega
        print("API RAW RESPONSE:", res.text)

        try:
            data = res.json()
            sim = data.get("sim", "N/A")
            operator = data.get("operator", "N/A")
            region = data.get("region", "N/A")
            response = (
                f"📞 Number info for {number}:\n"
                f"• SIM: {sim}\n"
                f"• Operator: {operator}\n"
                f"• Region: {region}"
            )
        except Exception:
            response = f"📞 Number info for {number}:\n{res.text.strip()}"

        await update.message.reply_text(response)

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# --------- MAIN FUNCTION ---------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("num", num))

    print("🤖 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
