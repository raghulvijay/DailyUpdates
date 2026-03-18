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
    yesterday_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
    yesterday_unix = int((now - timedelta(days=1)).timestamp())
    return yesterday_date, yesterday_unix

def fetch_all_stack_news():
    y_date, y_unix = get_yesterday_context()
    print(f"📡 Gathering Intelligence for {y_date}...")
    news_buffer = []

    # A. Hacker News
    try:
        hn_url = f"https://hn.algolia.com/api/v1/search?tags=story&numericFilters=created_at_i>{y_unix},points>100"
        hn_res = requests.get(hn_url, timeout=10).json()
        hits = hn_res.get('hits', [])
        # Safe slicing: check if hits exists and is a list
        if isinstance(hits, list):
            for hit in hits[:10]:
                news_buffer.append(f"[HN] {hit['title']} (URL: {hit.get('url')})")
    except Exception as e: print(f"⚠️ HN Error: {e}")

    # B. NewsData
    try:
        broad_query = "OpenAI OR Anthropic OR NVIDIA OR AI Agent OR DevOps OR ReactJS"
        url = f"https://newsdata.io/api/1/news?apikey={NEWS_DATA_KEY}&q={broad_query}&language=en"
        res = requests.get(url, timeout=15).json()
        articles = res.get('results', [])
        # FIX: Added check to ensure articles is a list before slicing
        if isinstance(articles, list):
            for art in articles[:10]:
                news_buffer.append(f"[News] {art.get('title')} (URL: {art.get('link')})")
    except Exception as e: print(f"⚠️ NewsData Error: {e}")

    return "\n".join(news_buffer)

def generate_full_brief(raw_content, retries=3):
    print("🧠 Gemini Architect: Summarizing today's Tech Pill...")
    today_str = datetime.now().strftime('%B %d, %Y')
    model_id = "gemini-2.5-flash-lite"
    
    prompt = (
        f"You are a Senior Technical Architect. Analyze these news items:\n{raw_content}\n\n"
        f"Create a 'Daily Tech Pill' report for a developer team. Use this EXACT structure:\n\n"
        f"# 💊 DAILY TECH PILL | {today_str}\n"
        f"**Vibe Check:** [One emoji + one sentence on the market mood]\n"
        f"**Architect’s Take:** [2 sentence high-level analysis of today's core shift]\n\n"
        f"### 🚀 TOP INDUSTRY SHAKERS\n"
        f"* **[Company] | [Feature]** ([URL])\n"
        f"  * **The What:** 1 sentence summary.\n"
        f"  * **The Impact:** 1 sentence why it matters.\n\n"
        f"### 🧠 LLM & MODEL UPDATES\n"
        f"* [Item] ([URL])\n\n"
        f"### 🤖 AGENT & FRAMEWORK UPDATES\n"
        f"* [Item] ([URL])\n\n"
        f"### 💻 FULL-STACK & DEVOPS UPDATES\n"
        f"* [Item] ([URL])\n\n"
        f"### 🔧 TECH & INFRASTRUCTURE\n"
        f"* [Item] ([URL])\n\n"
        f"### 💡 PROMPT OF THE DAY\n"
        f"**Goal:** Technical Growth\n"
        f"> [The actual prompt text]\n\n"
        f"Keep it professional and crispy. Ensure every item has a URL."
    )

    for i in range(retries):
        try:
            response = client.models.generate_content(model=model_id, contents=prompt)
            return response.text
        except Exception as e:
            # If we hit a rate limit (429), wait 70 seconds for the quota to reset
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print(f"⚠️ Quota hit. Waiting 70s for cooldown (Attempt {i+1}/{retries})...")
                time.sleep(70)
            else:
                print(f"⚠️ Attempt {i+1} failed: {e}")
                time.sleep(10)
    return "AI Generation Failed due to Quota Limits. Please try again in 1 hour."

def post_to_zoho(message):
    url = WEBHOOK_URL.strip() if WEBHOOK_URL else None
    if not url: return

    print("📤 Sending to Zoho Cliq...")
    try:
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
