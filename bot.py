import os
import logging
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from google import genai
from google.genai import types
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Environment Variables ရယူခြင်း ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Gemini Setup (Google GenAI SDK)
client = genai.Client(api_key=GEMINI_API_KEY)

# 🧠 ဘွတ်ကီကြေး မာယာများကိုပါ ထည့်သွင်းစဉ်းစားမည့် System Instruction
SYSTEM_INSTRUCTION = """
You are a professional football betting analyst and elite "Top Tipster." 
Your core expertise is reading bookmaker traps, analyzing handicap lines manipulation, and protecting multi-leg parlay (မောင်း) tickets.
Always respond strictly in professional, analytical Burmese language.
"""

# --- Render အတွက် Dummy Web Server (Port ဖွင့်ပေးရန်) ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running alive!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

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

    prompt = (
        f"Analyze this match for parlay betting stability and bookmaker odds traps:\n"
        f"Match: {text}\n"
        f"Please evaluate potential handicap lines, recent forms, head-to-head records, and provide the safest pick with Void/Push potential in professional Burmese language."
    )

    success = False
    last_error = None

    # အလွန်တည်ငြိမ်သော gemini-1.5-flash ကို အသုံးပြု၍ ၃ ကြိမ်အထိ စမ်းမည်
    for attempt in range(1, 4):
        try:
            response = await client.aio.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                )
            )
            if response and response.text:
                await update.message.reply_text(response.text, parse_mode="Markdown")
                success = True
                break
        except Exception as e:
            last_error = e
            logger.warning(f"Attempt {attempt} failed: {str(e)}")
            if attempt < 3:
                await asyncio.sleep(2)

    if not success:
        error_msg = str(last_error) if last_error else "Unknown error"
        logger.error(f"All attempts failed. Error: {error_msg}")
        await update.message.reply_text(f"⚠️ ဆာဗာ ချိတ်ဆက်မှု အဆင်မပြေပါ (Error: {error_msg[:120]})။ ကျေးဇူးပြု၍ ခဏနေမှ ထပ်ကြိုးစားပါ။")

if __name__ == "__main__":
    # 1. Start Dummy Server in background thread for Render Port Binding
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 2. Setup Telegram Application with timeout fixes
    request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0)
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).request(request).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze_match))
    
    print("Bot is running with stable Gemini 1.5 Flash...")
    app.run_polling()
