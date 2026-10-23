import os
import logging
import asyncio
import requests
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
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY") # Football API Key

# Gemini Setup (Google GenAI SDK)
client = genai.Client(api_key=GEMINI_API_KEY)

# 🧠 ဘွတ်ကီကြေး မာယာများကိုပါ ထည့်သွင်းစဉ်းစားမည့် System Instruction
SYSTEM_INSTRUCTION = """
You are a professional football betting analyst and elite "Top Tipster." 
Your core expertise is reading bookmaker traps, analyzing handicap lines manipulation, and protecting multi-leg parlay (မောင်း) tickets.
Analyze the provided live Football API data and respond strictly in professional, analytical Burmese language.
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

# --- RapidAPI (Football API) မှ အချက်အလက်ဆွဲထုတ်သည့် Function ---
def fetch_football_api_data(match_query):
    if not RAPIDAPI_KEY:
        return "RAPIDAPI_KEY not configured in environment variables."
    
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
    }
    # ဥပမာအနေဖြင့် လက်ရှိရရှိနိုင်သော fixture ဒေတာများကို တောင်းခံခြင်း
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            fixtures = data.get("response", [])
            if fixtures:
                # ရလာတဲ့ ဒေတာအချို့ကို စုစည်းပြီး စာသားပုံစံပြောင်းမည်
                summary_data = f"Fetched Live Football API Match Data for query '{match_query}':\n"
                for fix in fixtures[:5]: # ထိပ်ဆုံး ပွဲစဉ်အချို့ကို ထည့်မည်
                    home = fix['teams']['home']['name']
                    away = fix['teams']['away']['name']
                    league = fix['league']['name']
                    summary_data += f"- League: {league} | {home} vs {away}\n"
                return summary_data
            else:
                return f"Match query '{match_query}' API-Football တွင် တိုက်ရိုက်မတွေ့ရှိပါ။ သို့သော် အထွေထွေအချက်အလက်ဖြင့် ဆန်းစစ်ပေးပါ။"
        else:
            return f"Football API Error: Status {response.status_code}"
    except Exception as e:
        logger.error(f"Football API Connection Error: {str(e)}")
        return f"Football API Connection Failed: {str(e)}"

# --- Telegram Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🇲🇲 **Top Tipster Automated Bot (Pro Version)**\n\n"
        "စကရင်ရှော့တင်စရာမလိုပါ! Football API နှင့် Gemini AI တို့ကို ချိတ်ဆက်ထားပြီး ဘွတ်ကီကြေး မာယာများကို အလိုအလျောက် သုံးသပ်ပေးမည့် Bot ဖြစ်ပါသည်။\n\n"
        "👉 **အသုံးပြုပုံ:** ပွဲစဉ်ကို ဤသို့ ရိုက်ပို့ပါ - \n"
        "`Chelsea vs Tottenham Hotspur`"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def analyze_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "vs" not in text.lower():
        await update.message.reply_text("ကျေးဇူးပြု၍ ပုံစံမှန်ကန်စွာ ပို့ပေးပါ (ဥပမာ - Team A vs Team B)")
        return

    await update.message.reply_text("🔍 Football API မှ ပွဲစဉ်အချက်အလက်များနှင့် ဘွတ်ကီကြေးများကို ဆွဲထုတ်၍ သုံးသပ်နေပါသည်။ ခဏစောင့်ပေးပါ...")

    # ၁။ RapidAPI မှ အချက်အလက်များကို ဦးစွာ ဆွဲထုတ်မည်
    api_data = fetch_football_api_data(text)

    # ၂။ ဆွဲထုတ်ထားသော API ဒေတာများကို Prompt ထဲ ထည့်၍ Gemini ဆီ ပို့မည်
    prompt = (
        f"Analyze this match based on the following Football API data and bookmaker odds traps:\n"
        f"Match Request: {text}\n"
        f"API Live Data Retrieved: {api_data}\n\n"
        f"Please evaluate potential handicap lines, recent forms, and provide the safest pick with Void/Push potential in professional Burmese language."
    )

    success = False
    last_error = None

    # ၃။ Gemini 3.8 Flash (သို့မဟုတ် အသင့်တော်ဆုံး Model) ဖြင့် ၃ ကြိမ်အထိ ထပ်မံကြိုးစားမည့် Loop
    for attempt in range(1, 4):
        try:
            response = await client.aio.models.generate_content(
                model='gemini-3.8-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    thinking_config={'thinking_budget': 0}
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
    
    print("Bot is running with Football API and Gemini integration...")
    app.run_polling()
