import asyncio
import requests
from bs4 import BeautifulSoup
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, MessageHandler, CommandHandler,
    CallbackQueryHandler, filters, ContextTypes
)

from flask import Flask
from threading import Thread

# ---------------- FLASK KEEP ALIVE ----------------
app_web = Flask('')

@app_web.route('/')
def home():
    return "Bot is running!"

def run_web():
    app_web.run(host='0.0.0.0', port=10000)

def keep_alive():
    Thread(target=run_web).start()

# ---------------- TOKEN ----------------
TOKEN = "8608088596:AAGMJ6Euyiod2ec5ycfEJc1FcV_iHOR8AkA"

user_stop = {}
last_range = {}

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["🚀 Start"]]

    await update.message.reply_text(
        "🚀 Ready!",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ---------------- GET TRANSACTION ----------------
def get_tran_ids(roll):
    url = f"https://billpay.sonalibank.com.bd/DhakaCentralUniversity/Home/Search?searchStr={roll}"
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table")
        if not table:
            return []
        return [r.find_all("td")[1].text.strip() for r in table.find_all("tr")[1:]]
    except:
        return []

# ---------------- GET DATA ----------------
def get_data(tid):
    url = f"https://billpay.sonalibank.com.bd/DhakaCentralUniversity/Home/Voucher/{tid}"
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        lines = [l.strip() for l in soup.get_text("\n").split("\n") if l.strip()]

        def find(x):
            for i in range(len(lines)):
                if x in lines[i]:
                    return lines[i+1]
            return "N/A"

        name = find("Name")
        roll = find("Roll")
        serial = find("Serial")
        mobile = find("Mobile")
        amount = find("Amount")
        date = find("Date")

        if name == "N/A":
            return None, None

        text = f"""Transaction ID: {tid}
Name: {name}
Roll: {roll}
Serial: {serial}
Mobile: {mobile}
Amount(BDT): {amount}
Date: {date}"""

        return text, mobile

    except:
        return None, None

# ---------------- BUTTON ----------------
def contact_btn(mobile):
    if not mobile or mobile == "N/A":
        return None

    n = mobile.replace("+","").replace(" ","")
    if n.startswith("01"):
        n = "880" + n[1:]

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📱 WhatsApp", url=f"https://wa.me/{n}"),
            InlineKeyboardButton("✈️ Telegram", url=f"https://t.me/+{n}")
        ]
    ])

def stop_btn():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛑 Stop Search", callback_data="stop")]
    ])

def next_btn(num):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"➡️ Next {num}", callback_data="next")]
    ])

# ---------------- SEARCH ENGINE ----------------
async def run_search(message, start, end):
    uid = message.chat_id
    user_stop[uid] = False

    total = end - start + 1
    found = 0

    status = await message.reply_text("⏳ Starting...", reply_markup=stop_btn())

    for i, roll in enumerate(range(start, end+1), 1):

        if user_stop.get(uid):
            break

        tids = get_tran_ids(roll)

        for tid in tids:
            if user_stop.get(uid):
                break

            data, mobile = get_data(tid)
            if data:
                found += 1
                await message.reply_text(f"📄 Result {found}:\n{data}", reply_markup=contact_btn(mobile))

        try:
            await status.edit_text(
                f"⏳ Processing...\n🔢 Roll: {roll}\n📊 Found: {found}\n✅ Progress: {i}/{total}",
                reply_markup=stop_btn()
            )
        except:
            pass

        await asyncio.sleep(2)

    try:
        await status.delete()
    except:
        pass

    if user_stop.get(uid):
        await message.reply_text(f"🛑 Stopped!\n📊 Total: {found}")
    else:
        await message.reply_text(f"✅ Done!\n📊 Total: {found}")
        await message.reply_text(f"👉 Next {total}?", reply_markup=next_btn(total))

# ---------------- MESSAGE HANDLER ----------------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    uid = update.message.from_user.id

    # START BUTTON CLICK
    if text.lower() in ["🚀 start", "start"]:
        await update.message.reply_text("🚀 Ready!")
        return

    # SINGLE
    if text.isdigit():
        r = int(text)
        last_range[uid] = (r, r)
        await run_search(update.message, r, r)

    # RANGE
    elif "-" in text:
        try:
            s, e = map(int, text.split("-"))

            if (e - s + 1) > 500:
                await update.message.reply_text("❌ Max 500 limit")
                return

            last_range[uid] = (s, e)
            await run_search(update.message, s, e)

        except:
            await update.message.reply_text("❌ Format: 1000-1500")

# ---------------- BUTTON ACTION ----------------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id

    if q.data == "stop":
        user_stop[uid] = True
        await q.answer("🛑 Stopping...")

    elif q.data == "next":
        s, e = last_range.get(uid, (0,0))
        diff = e - s + 1
        ns, ne = e + 1, e + diff
        last_range[uid] = (ns, ne)

        await q.answer()
        await q.message.reply_text(f"🔄 Auto Search: {ns}-{ne}")
        await run_search(q.message, ns, ne)

# ---------------- MAIN ----------------
def main():
    keep_alive()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.add_handler(CallbackQueryHandler(button))

    print("🤖 BOT RUNNING FINAL...")
    app.run_polling()

if __name__ == "__main__":
    main()
