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

When analyzing the provided match data (which includes Both Teams' Last 10 Matches, H2H, and Handicap Odds):
1. **Odds Trap Detection (ဘွတ်ကီကြေး မာယာ):** Identify why bookmakers set specific handicap lines. Spot trap lines designed to lure public betting behavior.
2. **Form & H2H Reality Check:** Compare the recent 10 matches of both teams and head-to-head records to strip away superficial hype.
3. **Value & Safety Focus:** Prioritize low-risk, high-stability picks with "Push/Void" potential (such as -1, +1, +1.5) rather than high-risk spreads.
4. **Language:** Respond strictly in professional, analytical Burmese language.
"""

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_INSTRUCTION
)

# --- API-Football Data Fetching Functions ---
def get_team_id(team_name):
    """အသင်းအမည်မှစ၍ API-Football ရှိ Team ID ကို ရှာဖွေခြင်း"""
    url = f"https://api-football-v1.p.rapidapi.com/v3/teams?search={team_name}"
    headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            res = response.json().get("response", [])
            if res:
                return res[0]["team"]["id"]
    except Exception as e:
        logging.error(f"Error fetching team ID: {e}")
    return None

def get_recent_matches(team_id):
    """အသင်းတစ်သင်း၏ နောက်ဆုံး ၁၀ ပွဲ ရလဒ်များ ဆွဲယူခြင်း"""
    url = f"https://api-football-v1.p.rapidapi.com/v3/fixtures?team={team_id}&last=10"
    headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            matches = response.json().get("response", [])
            form_summary = []
            for m in matches:
                home = m["teams"]["home"]["name"]
                away = m["teams"]["away"]["name"]
                gh = m["goals"]["home"]
                ga = m["goals"]["away"]
                form_summary.append(f"{home} {gh}-{ga} {away}")
            return ", ".join(form_summary)
    except Exception as e:
        logging.error(f"Error fetching matches: {e}")
    return "Data unavailable"

# --- Telegram Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🇲🇲 **Top Tipster Automated Bot (Pro Version)**\n\n"
        "စကရင်ရှော့တင်စရာမလိုတော့ပါ! ဘွတ်ကီကြေး မာယာများနှင့် နောက်ဆုံး ၁၀ ပွဲ အချက်အလက်များပါ အလိုအလျောက် သုံးသပ်ပေးမည့် Bot ဖြစ်ပါသည်။\n\n"
        "👉 **အသုံးပြုပုံ:** ပွဲစဉ်ကို ဤသို့ ရိုက်ပို့ပါ - \n"
        "`Juventus vs Rennes`"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def analyze_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "vs" not in text.lower():
        await update.message.reply_text("ကျေးဇူးပြု၍ ပုံစံမှန်ကန်စွာ ပို့ပေးပါ (ဥပမာ - Team A vs Team B)")
        return

    await update.message.reply_text("🔍 ဘွတ်ကီကြေးများ၊ နှစ်သင်းလုံး၏ နောက်ဆုံး ၁၀ ပွဲနှင့် H2H အချက်အလက်များကို API မှ ဆွဲထုတ်နေပါပြီ...")

    try:
        parts = text.split("vs")
        team1_name = parts[0].strip()
        team2_name = parts[1].strip()

        # 1. Fetch Team IDs
        t1_id = get_team_id(team1_name)
        t2_id = get_team_id(team2_name)

        if not t1_id or not t2_id:
            await update.message.reply_text("❌ အသင်းအမည် ရှာမတွေ့ပါ။ စာလုံးပေါင်း သို့မဟုတ် အသင်းနာမည်ကို သေချာစစ်ဆေးပေးပါ။")
            return

        # 2. Fetch Recent Forms (Last 10 matches)
        t1_form = get_recent_matches(t1_id)
        t2_form = get_recent_matches(t2_id)

        # 3. Construct Deep Prompt for Gemini AI
        prompt = (
            f"Analyze this match for parlay betting stability:\n"
            f"Match: {team1_name} vs {team2_name}\n"
            f"--- {team1_name} (Home) Last 10 Matches: {t1_form}\n"
            f"--- {team2_name} (Away) Last 10 Matches: {t2_form}\n"
            f"Please evaluate bookmaker odds manipulation, handicap lines, and provide the safest pick with Void/Push potential in Burmese."
        )

        # 4. Generate AI Analysis
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
