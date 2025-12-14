import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Replace with your BotFather token
ADMIN_ID = 8456504803
CHANNEL_ID = -1003448152929  # Numeric channel ID
CHANNEL_LINK = "https://t.me/+XmDGUXMFHlI0OTU1"

# =============== DATABASE SETUP =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    points INTEGER DEFAULT 0,
    ref_by INTEGER
)""")
c.execute("""CREATE TABLE IF NOT EXISTS accounts(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT,
    password TEXT,
    used_count INTEGER DEFAULT 0
)""")
conn.commit()

# =============== START COMMAND =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    c.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (user_id,))
    conn.commit()

    keyboard = [
        [InlineKeyboardButton("🔔 Join Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ Verify", callback_data="verify")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Welcome! Join the channel first and verify to access the bot.",
        reply_markup=reply_markup
    )

# =============== CALLBACK QUERY =================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "verify":
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            # Show dashboard
            keyboard = [
                [InlineKeyboardButton("📩 Get Account", callback_data="get_account"),
                 InlineKeyboardButton("👥 Refer", callback_data="refer")],
                [InlineKeyboardButton("💰 Balance", callback_data="balance"),
                 InlineKeyboardButton("🏦 Withdraw", callback_data="withdraw")]
            ]
            await query.edit_message_text(
                "✅ You are verified! Here is your dashboard:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text("❌ Please join the channel first to continue.")

    # =============== DASHBOARD BUTTONS =================
    elif query.data == "get_account":
        c.execute("SELECT * FROM accounts WHERE used_count < 5 LIMIT 1")
        row = c.fetchone()
        if row:
            account_id, email, password, used_count = row
            c.execute("UPDATE accounts SET used_count=? WHERE id=?", (used_count+1, account_id))
            conn.commit()
            c.execute("UPDATE users SET points=points-2 WHERE user_id=?", (user_id,))
            conn.commit()
            await query.message.reply_text(f"📩 Here is your account:\nEmail: {email}\nPassword: {password}")
        else:
            await query.message.reply_text("❌ No accounts available now.")

    elif query.data == "refer":
        await query.message.reply_text(f"👥 Share this link to earn points:\nhttps://t.me/{context.bot.username}?start={user_id}\n1 referral = 1 point")

    elif query.data == "balance":
        c.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
        points = c.fetchone()[0]
        await query.message.reply_text(f"💰 Your balance: {points} points")

    elif query.data == "withdraw":
        await query.message.reply_text("🏦 Withdraw request sent. Admin will process it manually.")

# =============== MAIN =================
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.run_polling()
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT,
    password TEXT,
    used_count INTEGER DEFAULT 0
)
""")

conn.commit()

# ---------- HELPERS ----------
def get_user(uid):
    cur.execute("SELECT * FROM users WHERE telegram_id=?", (uid,))
    return cur.fetchone()

def add_user(uid, referred_by=None):
    cur.execute(
        "INSERT OR IGNORE INTO users (telegram_id, referred_by) VALUES (?,?)",
        (uid, referred_by)
    )
    conn.commit()

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    ref = None
    if context.args:
        try:
            ref = int(context.args[0])
        except:
            pass

    if ref == uid:
        ref = None  # block self-referral

    add_user(uid, ref)

    keyboard = [
        [InlineKeyboardButton("🔔 Join Channel", url=REQUIRED_CHANNEL)],
        [InlineKeyboardButton("✅ Verify", callback_data="verify")]
    ]

    await update.message.reply_text(
        "👋 Welcome!\n\nJoin the channel and click VERIFY to continue.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------- VERIFY ----------
async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id

    # Check membership of the private channel
    try:
        member = await context.bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=uid)
    except:
        await query.edit_message_text("❌ Cannot verify membership. Make sure you joined the channel correctly.")
        return

    if member.status not in ["member", "administrator", "creator"]:
        await query.edit_message_text("❌ Please join the private channel first.")
        return

    user = get_user(uid)
    if user and user[3] == 0:
        # First-time verification
        referred_by = user[2]

        if referred_by:
            # Add referral if not already counted
            cur.execute(
                "INSERT OR IGNORE INTO referrals (referrer, referred) VALUES (?,?)",
                (referred_by, uid)
            )
            if cur.rowcount:
                # Add points to referrer
                cur.execute(
                    "UPDATE users SET points = points + ? WHERE telegram_id=?",
                    (REFERRAL_REWARD, referred_by)
                )

        # Mark user as verified
        cur.execute(
            "UPDATE users SET verified=1 WHERE telegram_id=?",
            (uid,)
        )
        conn.commit()

    # Show main dashboard
    keyboard = [
        [InlineKeyboardButton("📩 Get Account", callback_data="get")],
        [InlineKeyboardButton("👥 Refer", callback_data="refer")],
        [InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("🏦 Withdraw", callback_data="withdraw")]
    ]

    await query.edit_message_text(
        "🎌 Dashboard\n\nChoose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------- GET ACCOUNT ----------
async def get_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    user = get_user(uid)
    if user[1] < ACCOUNT_COST:
        await query.edit_message_text("❌ Not enough points.")
        return

    cur.execute(
        "SELECT * FROM accounts WHERE used_count < ? ORDER BY id LIMIT 1",
        (MAX_USERS_PER_ACCOUNT,)
    )
    acc = cur.fetchone()

    if not acc:
        await query.edit_message_text("❌ No accounts available right now.")
        return

    # Increment account usage and deduct points
    cur.execute(
        "UPDATE accounts SET used_count = used_count + 1 WHERE id=?",
        (acc[0],)
    )
    cur.execute(
        "UPDATE users SET points = points - ? WHERE telegram_id=?",
        (ACCOUNT_COST, uid)
    )
    conn.commit()

    await query.edit_message_text(
        f"✅ Account Details:\n\nEmail: `{acc[1]}`\nPassword: `{acc[2]}`",
        parse_mode="Markdown"
    )

# ---------- REFER ----------
async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    await query.answer()

    link = f"https://t.me/{context.bot.username}?start={uid}"

    await query.edit_message_text(
        f"👥 Refer & Earn\n\n"
        f"Share this link with friends:\n{link}\n\n"
        f"1 referral = 1 point"
    )

# ---------- BALANCE ----------
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    await query.answer()

    user = get_user(uid)
    await query.edit_message_text(f"💰 Your balance: {user[1]} points")

# ---------- WITHDRAW ----------
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🏦 Withdraw Request\n\n"
        "Send your withdrawal request to the admin with:\n"
        "• Your username\n"
        "• Payment method (UPI/Wallet)\n\n"
        "Admin will process manually."
    )

# ---------- ADMIN ADD ACCOUNT ----------
async def add_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        data = " ".join(context.args)
        email, password = data.split("|")
    except:
        await update.message.reply_text("Usage: /add email|password")
        return

    cur.execute(
        "INSERT INTO accounts (email, password) VALUES (?,?)",
        (email.strip(), password.strip())
    )
    conn.commit()

    await update.message.reply_text("✅ Account added successfully.")

# ---------- MAIN ----------
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add_account))
app.add_handler(CallbackQueryHandler(verify, pattern="verify"))
app.add_handler(CallbackQueryHandler(get_account, pattern="get"))
app.add_handler(CallbackQueryHandler(refer, pattern="refer"))
app.add_handler(CallbackQueryHandler(balance, pattern="balance"))
app.add_handler(CallbackQueryHandler(withdraw, pattern="withdraw"))

app.run_polling()
