import os
import sqlite3
import logging
from datetime import datetime
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ---------- CONFIG (env fallback to values you provided) ----------
BOT_TOKEN = os.getenv("BOT_TOKEN", "8277485140:AAERBu7ErxHReWZxcYklneU1wEXY--I_32c")
try:
    OWNER_ID = int(os.getenv("OWNER_ID", "8270660057"))
except:
    OWNER_ID = 8270660057

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "/Dipak")

CHANNEL_A_ID = int(os.getenv("CHANNEL_A_ID", "-1002851939876"))
CHANNEL_A_LINK = os.getenv("CHANNEL_A_LINK", "https://t.me/+eB_J_ExnQT0wZDU9")
CHANNEL_B_USERNAME = os.getenv("CHANNEL_B_USERNAME", "@taskblixosint")
CHANNEL_B_LINK = os.getenv("CHANNEL_B_LINK", "http://t.me/taskblixosint")

try:
    NEW_USER_CREDITS = int(os.getenv("NEW_USER_CREDITS", "2"))
    REFERRAL_BONUS = int(os.getenv("REFERRAL_BONUS", "1"))
except:
    NEW_USER_CREDITS = 2
    REFERRAL_BONUS = 1

OWNER_CONTACT = os.getenv("OWNER_CONTACT", "@HIDANCODE")

LEAK_API_URL = os.getenv("LEAK_API_URL", "https://leakosintapi.com/")
LEAK_API_KEY = os.getenv("LEAK_API_KEY", "7658050410:qQ88TxXl")

DB_PATH = os.getenv("DB_PATH", "botdata.db")

# ---------- BOT INIT ----------
bot = telebot.TeleBot(BOT_TOKEN)

# wrap get_me in try to avoid crashing on start if network not ready
try:
    me = bot.get_me()
    BOT_USERNAME = me.username if me and getattr(me, "username", None) else "this_bot"
    logging.info(f"Bot started as @{BOT_USERNAME}")
except Exception as e:
    BOT_USERNAME = "this_bot"
    logging.warning(f"Could not call get_me(): {e}. Continuing, but bot info may be incomplete.")

# ---------- DATABASE ----------
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users(
  user_id INTEGER PRIMARY KEY,
  username TEXT,
  credits INTEGER DEFAULT 0,
  referred_by INTEGER,
  referrals_count INTEGER DEFAULT 0,
  banned INTEGER DEFAULT 0,
  created_at TEXT
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

# ---------- HELPERS ----------
def get_user(uid):
    c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    r = c.fetchone()
    if not r:
        return None
    return {
        "user_id": r[0],
        "username": r[1],
        "credits": r[2],
        "referred_by": r[3],
        "referrals_count": r[4],
        "banned": r[5],
        "created_at": r[6]
    }

def create_user(uid, username, referred_by=None):
    if get_user(uid):
        return False
    now = datetime.utcnow().isoformat()
    c.execute(
        "INSERT INTO users(user_id, username, credits, referred_by, referrals_count, banned, created_at) VALUES(?,?,?,?,?,?,?)",
        (uid, username, NEW_USER_CREDITS, referred_by, 0, 0, now)
    )
    conn.commit()

    # Give referral bonus if valid referred_by
    if referred_by and referred_by != uid and get_user(referred_by):
        c.execute("UPDATE users SET credits = credits + ?, referrals_count = referrals_count + 1 WHERE user_id=?",
                  (REFERRAL_BONUS, referred_by))
        c.execute("UPDATE users SET credits = credits + ? WHERE user_id=?", (REFERRAL_BONUS, uid))
        conn.commit()

    log(uid, f"create_user referred_by={referred_by}")
    logging.info(f"Created user {uid} username={username} referred_by={referred_by}")
    return True

def add_credits(uid, n):
    c.execute("UPDATE users SET credits = credits + ? WHERE user_id=?", (n, uid))
    conn.commit()
    log(uid, f"add_credits {n}")
    logging.info(f"Added {n} credits to {uid}")

def deduct_credit(uid, n=1):
    u = get_user(uid)
    if not u:
        return False
    if u["credits"] < n:
        return False
    c.execute("UPDATE users SET credits = credits - ? WHERE user_id=?", (n, uid))
    conn.commit()
    log(uid, f"deduct {n}")
    logging.info(f"Deducted {n} credit(s) from {uid}")
    return True

def log(user_id, action):
    now = datetime.utcnow().isoformat()
    c.execute("INSERT INTO logs(user_id, action, created_at) VALUES(?,?,?)", (user_id, action, now))
    conn.commit()

def is_member_of(chat_id_or_username, user_id):
    """
    chat_id_or_username: can be integer chat_id (e.g. -100...) or username string "@channel"
    """
    try:
        m = bot.get_chat_member(chat_id_or_username, user_id)
        return m.status in ("member", "administrator", "creator")
    except Exception as e:
        logging.debug(f"is_member_of error for {chat_id_or_username} user {user_id}: {e}")
        return False

def is_verified(uid):
    # Check membership in Channel A (by id) and Channel B (by username)
    a_ok = is_member_of(CHANNEL_A_ID, uid)
    chb = CHANNEL_B_USERNAME if CHANNEL_B_USERNAME.startswith("@") else f"@{CHANNEL_B_USERNAME}"
    b_ok = is_member_of(chb, uid)
    logging.debug(f"is_verified for {uid}: channel_a={a_ok}, channel_b={b_ok}")
    return a_ok and b_ok

def join_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📢 Join Channel 1", url=CHANNEL_A_LINK))
    kb.add(InlineKeyboardButton("📣 Join Channel 2", url=CHANNEL_B_LINK))
    kb.add(InlineKeyboardButton("✅ I have Joined (Verify)", callback_data="verify"))
    return kb

def is_admin(uid):
    return uid == OWNER_ID

# ---------- HANDLERS ----------

@bot.message_handler(commands=["start"])
def cmd_start(m):
    try:
        uid = m.from_user.id
        uname = m.from_user.username or (m.from_user.first_name or "") + (" " + (m.from_user.last_name or "") if getattr(m.from_user, "last_name", None) else "")
        # Parse referral parameter if present: "/start ref_123"
        ref = None
        text = (m.text or "").strip()
        parts = text.split(" ", 1)
        if len(parts) > 1 and parts[1].startswith("ref_"):
            try:
                ref = int(parts[1].replace("ref_", ""))
            except:
                ref = None

        create_user(uid, uname, ref)
        u = get_user(uid) or {}

        if u.get("banned"):
            bot.reply_to(m, "🚫 You are banned. Contact owner.")
            return

        if not is_verified(uid):
            bot.reply_to(m, "🔒 You must join the channels first:", reply_markup=join_kb())
            return

        welcome_msg = (
            f"👋 Hello {m.from_user.first_name or ''}!\n"
            f"💳 Your Credits: {u.get('credits', 0)}\n\n"
            "📌 How to use this bot:\n"
            "1. To check a number: `/num <phone_number>`\n"
            "2. To get your credits: `/credits`\n"
            f"3. Admin Panel: send `{ADMIN_PASSWORD}`\n"
            f"4. For help or contact: {OWNER_CONTACT}\n\n"
            "🔗 Make sure you stay joined in both channels."
        )
        bot.reply_to(m, welcome_msg, parse_mode="Markdown")
    except Exception as e:
        logging.exception("Error in /start handler")
        bot.reply_to(m, f"❌ An error occurred: {e}")

@bot.message_handler(commands=["credits"])
def cmd_credits(m):
    uid = m.from_user.id
    u = get_user(uid)
    if not u:
        bot.reply_to(m, "User not found. Use /start first.")
        return
    bot.reply_to(m, f"💳 You have {u['credits']} credits.")

@bot.message_handler(commands=["num"])
def cmd_num(m):
    uid = m.from_user.id
    u = get_user(uid)
    if not u:
        bot.reply_to(m, "❌ Use /start first to register.")
        return
    if u.get("banned"):
        bot.reply_to(m, "🚫 You are banned. Contact owner.")
        return
    if not is_verified(uid):
        bot.reply_to(m, "🔒 You must join the channels first.", reply_markup=join_kb())
        return

    parts = (m.text or "").split(" ", 1)
    if len(parts) < 2 or not parts[1].strip():
        bot.reply_to(m, "❌ Usage: /num <phone_number>")
        return
    number = parts[1].strip()

    if not deduct_credit(uid, 1):
        bot.reply_to(m, "❌ You don't have enough credits.")
        return

    try:
        headers = {"Authorization": f"Bearer {LEAK_API_KEY}"} if LEAK_API_KEY else {}
        params = {"number": number}
        res = requests.get(LEAK_API_URL, params=params, headers=headers, timeout=12)
        if res.status_code != 200:
            raise ValueError(f"API returned HTTP {res.status_code}")
        # try parse json safely
        data = {}
        try:
            data = res.json()
        except Exception:
            # fallback to text
            logging.debug("API returned non-JSON; using raw text")
            text = res.text.strip()
            response = f"📞 Number info for {number}:\n{text}"
            bot.reply_to(m, response)
            return

        sim_info = data.get("sim", "N/A")
        operator = data.get("operator", "N/A")
        region = data.get("region", "N/A")
        extra = data.get("extra", None)

        response_lines = [
            f"📞 Number info for {number}:",
            f"- SIM Info: {sim_info}",
            f"- Operator: {operator}",
            f"- Region: {region}"
        ]
        if extra:
            response_lines.append(f"- Extra: {extra}")

        response = "\n".join(response_lines)
    except Exception as e:
        logging.exception("Error fetching number info")
        response = f"❌ Failed to fetch number info: {str(e)}"

    bot.reply_to(m, response)

# Admin access via exact message (ADMIN_PASSWORD)
@bot.message_handler(func=lambda m: (m.text or "").strip() == ADMIN_PASSWORD)
def admin_panel(m):
    uid = m.from_user.id
    if not is_admin(uid):
        bot.reply_to(m, "❌ You are not authorized.")
        return
    admin_msg = (
        "👑 Admin Panel:\n\n"
        "1. Add credits: /addcredits <user_id> <amount>\n"
        "2. Ban user: /ban <user_id>\n"
        "3. Check logs: /logs\n"
        "4. Check balance: /balance <user_id>\n"
    )
    bot.reply_to(m, admin_msg)

@bot.message_handler(commands=["balance"])
def cmd_balance(m):
    uid = m.from_user.id
    if not is_admin(uid):
        bot.reply_to(m, "❌ You are not authorized.")
        return
    parts = (m.text or "").split()
    if len(parts) != 2:
        bot.reply_to(m, "Usage: /balance <user_id>")
        return
    try:
        target_uid = int(parts[1])
        u = get_user(target_uid)
        if not u:
            bot.reply_to(m, "User not found.")
            return
        bot.reply_to(m, f"💳 User {target_uid} has {u['credits']} credits.")
    except Exception:
        bot.reply_to(m, "❌ Invalid input.")

@bot.message_handler(commands=["addcredits"])
def cmd_addcredits(m):
    uid = m.from_user.id
    if not is_admin(uid):
        bot.reply_to(m, "❌ You are not authorized.")
        return
    parts = (m.text or "").split()
    if len(parts) != 3:
        bot.reply_to(m, "Usage: /addcredits <user_id> <amount>")
        return
    try:
        target_uid = int(parts[1])
        amount = int(parts[2])
        add_credits(target_uid, amount)
        bot.reply_to(m, f"✅ Added {amount} credits to {target_uid}")
    except Exception:
        bot.reply_to(m, "❌ Invalid input.")

@bot.message_handler(commands=["ban"])
def cmd_ban(m):
    uid = m.from_user.id
    if not is_admin(uid):
        bot.reply_to(m, "❌ You are not authorized.")
        return
    parts = (m.text or "").split()
    if len(parts) != 2:
        bot.reply_to(m, "Usage: /ban <user_id>")
        return
    try:
        target_uid = int(parts[1])
        c.execute("UPDATE users SET banned=1 WHERE user_id=?", (target_uid,))
        conn.commit()
        log(uid, f"ban {target_uid}")
        bot.reply_to(m, f"🚫 User {target_uid} has been banned.")
    except Exception:
        bot.reply_to(m, "❌ Invalid input.")

@bot.message_handler(commands=["logs"])
def cmd_logs(m):
    uid = m.from_user.id
    if not is_admin(uid):
        bot.reply_to(m, "❌ You are not authorized.")
        return
    c.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 10")
    logs = c.fetchall()
    if not logs:
        bot.reply_to(m, "No logs found.")
        return
    msg_lines = []
    for l in logs:
        # l = (id, user_id, action, created_at)
        msg_lines.append(f"{l[0]} | User {l[1]} | {l[2]} | {l[3]}")
    msg = "📝 Last 10 logs:\n\n" + "\n".join(msg_lines)
    bot.reply_to(m, msg)

# VERIFY CALLBACK
@bot.callback_query_handler(func=lambda call: call.data == "verify")
def cb_verify(call):
    uid = call.from_user.id
    try:
        if is_verified(uid):
            bot.answer_callback_query(call.id, "✅ Verified")
            # edit the original message to show verified
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="✅ Verified! Use /start")
        else:
            bot.answer_callback_query(call.id, "❌ Not verified. Join both channels.", show_alert=True)
    except Exception as e:
        logging.exception("Error in verify callback")
        try:
            bot.answer_callback_query(call.id, "❌ Verification check failed.", show_alert=True)
        except:
            pass

# ---------- RUN BOT ----------
if __name__ == "__main__":
    logging.info("Bot is starting (polling)...")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except KeyboardInterrupt:
        logging.info("Bot stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logging.exception(f"Bot stopped with error: {e}")    
