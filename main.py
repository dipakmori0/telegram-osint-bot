import os
import sqlite3
from datetime import datetime
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ===== CONFIG =====
BOT_TOKEN = "8277485140:AAERBu7ErxHReWZxcYklneU1wEXY--I_32c"
OWNER_ID = 8270660057

CHANNEL_A_ID = -1002851939876
CHANNEL_A_LINK = "https://t.me/+eB_J_ExnQT0wZDU9"
CHANNEL_B_USERNAME = "@taskblixosint"
CHANNEL_B_LINK = "http://t.me/taskblixosint"

NEW_USER_CREDITS = 2
REFERRAL_BONUS = 1
OWNER_CONTACT = "@HIDANCODE"

LEAK_API_URL = "https://leakosintapi.com/"
LEAK_API_KEY = "7658050410:qQ88TxXl"
VEHICLE_API_BASE = "https://vehicleinfo.zerovault.workers.dev/?VIN="

DB_PATH = "botdata.db"

# ===== BOT INIT =====
bot = telebot.TeleBot(BOT_TOKEN)
me = bot.get_me()
BOT_USERNAME = me.username if me and me.username else "this_bot"

# ===== DATABASE =====
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

c.execute("""
CREATE TABLE IF NOT EXISTS codes(
  code TEXT PRIMARY KEY,
  credits INTEGER,
  used INTEGER DEFAULT 0,
  created_by INTEGER,
  created_at TEXT
);
""")

conn.commit()

# ===== HELPERS =====
def get_user(uid):
    c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    r = c.fetchone()
    if not r: return None
    return {"user_id": r[0], "username": r[1], "credits": r[2], "referred_by": r[3], "referrals_count": r[4], "banned": r[5], "created_at": r[6]}

def create_user(uid, username, referred_by=None):
    if get_user(uid): return False
    now = datetime.utcnow().isoformat()
    c.execute("INSERT INTO users(user_id, username, credits, referred_by, referrals_count, banned, created_at) VALUES(?,?,?,?,?,?,?)",
              (uid, username, NEW_USER_CREDITS, referred_by, 0, 0, now))
    conn.commit()
    # Referral bonus
    if referred_by and referred_by != uid and get_user(referred_by):
        c.execute("UPDATE users SET credits = credits + ?, referrals_count = referrals_count + 1 WHERE user_id=?",
                  (REFERRAL_BONUS, referred_by))
        c.execute("UPDATE users SET credits = credits + ? WHERE user_id=?", (REFERRAL_BONUS, uid))
        conn.commit()
    log(uid, f"create_user referred_by={referred_by}")
    return True

def add_credits(uid, n):
    c.execute("UPDATE users SET credits = credits + ? WHERE user_id=?", (n, uid))
    conn.commit()
    log(uid, f"add_credits {n}")

def deduct_credit(uid, n=1):
    u = get_user(uid)
    if not u or u["credits"] < n: return False
    c.execute("UPDATE users SET credits = credits - ? WHERE user_id=?", (n, uid))
    conn.commit()
    log(uid, f"deduct {n}")
    return True

def log(user_id, action):
    now = datetime.utcnow().isoformat()
    c.execute("INSERT INTO logs(user_id, action, created_at) VALUES(?,?,?)", (user_id, action, now))
    conn.commit()

# ===== VERIFICATION =====
def is_member_of(chat_id, user_id):
    try:
        m = bot.get_chat_member(chat_id, user_id)
        return m.status in ("member", "administrator", "creator")
    except:
        return False

def is_verified(uid):
    a_ok = is_member_of(CHANNEL_A_ID, uid)
    chb = CHANNEL_B_USERNAME if CHANNEL_B_USERNAME.startswith("@") else f"@{CHANNEL_B_USERNAME}"
    b_ok = is_member_of(chb, uid)
    return a_ok and b_ok

def join_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📢 Join Channel 1", url=CHANNEL_A_LINK))
    kb.add(InlineKeyboardButton("📣 Join Channel 2", url=CHANNEL_B_LINK))
    kb.add(InlineKeyboardButton("✅ I have Joined (Verify)", callback_data="verify"))
    return kb

# ===== START COMMAND =====
@bot.message_handler(commands=["start"])
def cmd_start(m):
    uid = m.from_user.id
    uname = m.from_user.username or m.from_user.first_name or ""
    
    # Referral
    ref = None
    parts = m.text.split(" ", 1)
    if len(parts) > 1 and parts[1].startswith("ref_"):
        try:
            ref = int(parts[1].replace("ref_", ""))
        except:
            ref = None

    create_user(uid, uname, ref)
    u = get_user(uid)
    if u.get("banned"):
        bot.reply_to(m, "🚫 You are banned. Contact owner.")
        return

    if not is_verified(uid):
        bot.reply_to(m, "🔒 You must join the channels first:", reply_markup=join_kb())
        return
    
    # Welcome + Instructions
    welcome_msg = f"""
👋 Hello {m.from_user.first_name}!
💳 Your Credits: {u['credits']}

📌 How to use this bot:
1. To check a number: `/num <phone_number>`
2. To get your credits: `/credits`
3. For help or contact: {OWNER_CONTACT}

🔗 Make sure you stay joined in both channels.
"""
    bot.reply_to(m, welcome_msg, parse_mode="Markdown")

# ===== CREDITS COMMAND =====
@bot.message_handler(commands=["credits"])
def cmd_credits(m):
    uid = m.from_user.id
    u = get_user(uid)
    if not u:
        bot.reply_to(m, "User not found. Use /start first.")
        return
    bot.reply_to(m, f"💳 You have {u['credits']} credits.")

# ===== NUMBER COMMAND =====
@bot.message_handler(commands=["num"])
def cmd_num(m):
    uid = m.from_user.id
    u = get_user(uid)
    if not u:
        bot.reply_to(m, "❌ Use /start first to register.")
        return
    if not is_verified(uid):
        bot.reply_to(m, "🔒 You must join the channels first.", reply_markup=join_kb())
        return
    parts = m.text.split(" ", 1)
    if len(parts) < 2:
        bot.reply_to(m, "❌ Usage: /num <phone_number>")
        return
    number = parts[1].strip()
    if not deduct_credit(uid, 1):
        bot.reply_to(m, "❌ You don't have enough credits.")
        return
    # Example: call your API here (replace with real API)
    response = f"📞 Number info for {number}:\n- SIM Info: Example\n- Operator: Example\n- Region: Example"
    bot.reply_to(m, response)

# ===== VERIFY CALLBACK =====
@bot.callback_query_handler(func=lambda call: call.data == "verify")
def cb_verify(call):
    uid = call.from_user.id
    if is_verified(uid):
        bot.answer_callback_query(call.id, "✅ Verified")
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="✅ Verified! Use /start")
    else:
        bot.answer_callback_query(call.id, "❌ Not verified. Join both channels.", show_alert=True)

# ===== RUN BOT =====
bot.infinity_polling()
