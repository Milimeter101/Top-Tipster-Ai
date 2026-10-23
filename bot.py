import os
import requests
import logging
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Logging setup
logging.basicConfig(level=logging.INFO)

# --- Environment Variables ရယူခြင်း ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")

# Gemini Setup
genai.configure(api_key=GEMINI_API_KEY)

# 🧠 ဘွတ်ကီကြေး မာယာများကိုပါ ထည့်သွင်းစဉ်းစားမည့် System Instruction
SYSTEM_INSTRUCTION = """
You are a professional football betting analyst and elite "Top Tipster." 
Your core expertise is reading bookmaker traps, analyzing handicap lines manipulation, and protecting multi-leg parlay (မောင်း) tickets.
Always respond strictly in professional, analytical Burmese language.
"""

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_INSTRUCTION
)

# --- Telegram Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🇲🇲 **Top Tipster Automated Bot (Pro Version)**\n\n"
        "စကရင်ရှော့တင်စရာမလိုတော့ပါ! ဘွတ်ကီကြေး မာယာများနှင့် ပွဲစဉ်အချက်အလက်များကို အလိုအလျောက် သုံးသပ်ပေးမည့် Bot ဖြစ်ပါသည်။\n\n"
        "👉 **အသုံးပြုပုံ:** ပွဲစဉ်ကို ဤသို့ ရိုက်ပို့ပါ - \n"
        "`Juventus vs Rennes`"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def analyze_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "vs" not in text.lower():
        await update.message.reply_text("ကျေးဇူးပြု၍ ပုံစံမှန်ကန်စွာ ပို့ပေးပါ (ဥပမာ - Team A vs Team B)")
        return

    await update.message.reply_text("🔍 ပွဲစဉ်အချက်အလက်များနှင့် ဘွတ်ကီကြေးများကို စစ်ဆေး၍ သုံးသပ်နေပါသည်။ ခဏစောင့်ပေးပါ...")

    try:
        # Prompt construction for Gemini AI analysis
        prompt = (
            f"Analyze this match for parlay betting stability and bookmaker odds traps:\n"
            f"Match: {text}\n"
            f"Please evaluate potential handicap lines, recent forms, head-to-head records, and provide the safest pick with Void/Push potential in professional Burmese language."
        )

        # Generate AI Analysis
        response = model.generate_content(prompt)
        await update.message.reply_text(response.text, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error ဖြစ်ပေါ်နေပါသည်: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze_match))
    print("Bot is running...")
    app.run_polling()
