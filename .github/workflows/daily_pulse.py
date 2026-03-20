import requests
import os
import time
from datetime import datetime, timedelta
from google import genai

# 1. Configuration
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
NEWS_DATA_KEY = os.getenv("NEWS_DATA_KEY")

client = genai.Client(api_key=GEMINI_KEY)

def get_yesterday_context():
    now = datetime.now()
    yesterday_date_obj = now - timedelta(days=1)
    yesterday_str = yesterday_date_obj.strftime('%B %d, %Y')
    yesterday_iso = yesterday_date_obj.strftime('%Y-%m-%d')
    yesterday_unix = int(yesterday_date_obj.timestamp())
    return yesterday_str, yesterday_iso, yesterday_unix

def fetch_all_stack_news():
    _, y_iso, y_unix = get_yesterday_context()
    print(f"📡 Gathering Intelligence for {y_iso}...")
    news_buffer = []

    try:
        hn_url = f"https://hn.algolia.com/api/v1/search?tags=story&numericFilters=created_at_i>{y_unix},points>100"
        hn_res = requests.get(hn_url, timeout=10).json()
        hits = hn_res.get('hits', [])
        if isinstance(hits, list):
            for hit in hits[:10]:
                news_buffer.append(f"[HN] {hit['title']} (URL: {hit.get('url')})")
    except Exception as e: print(f"⚠️ HN Error: {e}")

    try:
        broad_query = "OpenAI OR Anthropic OR NVIDIA OR AI Agent OR DevOps OR ReactJS"
        url = f"https://newsdata.io/api/1/news?apikey={NEWS_DATA_KEY}&q={broad_query}&language=en"
        res = requests.get(url, timeout=15).json()
        articles = res.get('results', [])
        if isinstance(articles, list):
            for art in articles[:10]:
                news_buffer.append(f"[News] {art.get('title')} (URL: {art.get('link')})")
    except Exception as e: print(f"⚠️ NewsData Error: {e}")

    return "\n".join(news_buffer)

def generate_full_brief(raw_content, retries=3):
    yesterday_display_date, _, _ = get_yesterday_context()
    print(f"🧠 Gemini Architect: Summarizing Tech for {yesterday_display_date}...")
    
    model_id = "gemini-2.5-flash-lite"
    
    # UPDATED PROMPT: Uses HTML <b> for bolding and adds Problem/Solution context
    prompt = (
        f"You are a Lead Technical Instructor. Analyze these news items from {yesterday_display_date}:\n{raw_content}\n\n"
        f"Goal: Help a beginner developer learn AI through 'Problem vs Solution' analysis.\n\n"
        f"FORMATTING RULE:\n"
        f"1. DO NOT use asterisks (**) for bolding.\n"
        f"2. Use HTML <b> tags for bolding. Example: <b>The Problem:</b>\n"
        f"3. Ensure every news item includes its URL.\n\n"
        f"STRUCTURE:\n"
        f"# 💊 DAILY TECH PILL | {yesterday_display_date}\n"
        f"<b>Vibe Check:</b> [Emoji + Mood Summary]\n"
        f"<b>Architect’s Take:</b> [2 sentence analysis of why today matters]\n\n"
        f"### 🚀 TOP INDUSTRY SHAKERS\n"
        f"* <b>[Company] | [Feature]</b> ([URL])\n"
        f"  * <b>The Source:</b> [1 sentence on who the publisher is]\n"
        f"  * <b>The Problem:</b> [Explain the technical gap or pain point this update addresses]\n"
        f"  * <b>The Solution:</b> [Explain how this specific update/model solves that gap]\n"
        f"  * <b>The Impact:</b> [How it changes our development workflow]\n\n"
        f"### 🧠 LLM & MODEL UPDATES\n"
        f"### 🤖 AGENT & FRAMEWORK UPDATES\n"
        f"### 💻 FULL-STACK & DEVOPS UPDATES\n"
        f"### 🔧 TECH & INFRASTRUCTURE\n\n"
        f"### 💡 PROMPT OF THE DAY\n"
        f"<b>Goal:</b> Technical Growth\n"
        f"> [The actual prompt text]\n"
    )

    for i in range(retries):
        try:
            response = client.models.generate_content(model=model_id, contents=prompt)
            return response.text
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print(f"⚠️ Quota hit. Waiting 70s for cooldown...")
                time.sleep(70)
            else:
                print(f"⚠️ Attempt {i+1} failed: {e}")
                time.sleep(10)
    return "AI Generation Failed."

def post_to_zoho(message):
    url = WEBHOOK_URL.strip() if WEBHOOK_URL else None
    if not url: return

    print("📤 Sending to Zoho Cliq...")
    try:
        # We send raw text because Cliq interprets HTML tags (<b>) automatically
        res = requests.post(url, json={"text": message}, timeout=15)
        res.raise_for_status()
        print("✅ Daily Pill Delivered.")
    except Exception as e: 
        print(f"❌ Zoho Error: {e}")

if __name__ == "__main__":
    data = fetch_all_stack_news()
    if data:
        brief = generate_full_brief(data)
        post_to_zoho(brief)
