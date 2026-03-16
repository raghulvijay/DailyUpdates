import requests
import os
import time
from datetime import datetime, timedelta
from google import genai
from google.genai import types

# 1. Configuration
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
NEWS_DATA_KEY = os.getenv("NEWS_DATA_KEY")

# Debugging prints for GitHub Logs
if not WEBHOOK_URL: print("❌ ERROR: WEBHOOK_URL is missing!")
if not GEMINI_KEY: print("❌ ERROR: GEMINI_API_KEY is missing!")
if not NEWS_DATA_KEY: print("❌ ERROR: NEWS_DATA_KEY is missing!")

client = genai.Client(api_key=GEMINI_KEY)

def get_yesterday_context():
    now = datetime.now()
    yesterday_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
    yesterday_unix = int((now - timedelta(days=1)).timestamp())
    return yesterday_date, yesterday_unix

def fetch_all_stack_news():
    y_date, y_unix = get_yesterday_context()
    print(f"📡 Gathering All-Stack Intelligence for {y_date}...")
    news_buffer = []

    # A. Hacker News
    try:
        hn_url = f"https://hn.algolia.com/api/v1/search?tags=story&numericFilters=created_at_i>{y_unix},points>100"
        hn_res = requests.get(hn_url, timeout=10).json()
        for hit in hn_res.get('hits', [])[:8]:
            news_buffer.append(f"[Trending] {hit['title']} (URL: {hit.get('url')})")
    except Exception as e: print(f"⚠️ HN Error: {e}")

    # B. NewsData
    try:
        broad_query = "Artificial Intelligence OR LLM OR Cybersecurity OR ReactJS OR DevOps"
        url = f"https://newsdata.io/api/1/news?apikey={NEWS_DATA_KEY}&q={broad_query}&language=en&from_date={y_date}"
        res = requests.get(url, timeout=15).json()
        articles = res.get('results', [])
        if articles:
            count = min(len(articles), 12) 
            for i in range(count):
                news_buffer.append(f"[News] {articles[i]['title']} (Source: {articles[i].get('source_id')})")
    except Exception as e: print(f"⚠️ NewsData Error: {e}")

    return "\n".join(news_buffer)

def generate_full_brief(raw_content, retries=3):
    print("🧠 Gemini Deep Dive: Analyzing All-Stack Trends...")
    y_date, _ = get_yesterday_context()
    yesterday_str = datetime.strptime(y_date, '%Y-%m-%d').strftime('%B %d, %Y')
    
    model_id = "gemini-2.5-flash-lite"
    
    prompt = (
        f"You are a Senior Technical Architect. Analyze these updates from the last 24h:\n{raw_content}\n\n"
        f"STRUCTURE:\n# 🚀 TOP AI DEEP-DIVE | {yesterday_str}\n"
        "**[Title]**\n*Impact*: [2 sentences]\n\n---\n\n"
        "# 🤖 AI & MACHINE LEARNING\n* [Item 1]\n* [Item 2]\n\n"
        "---\n\n# 💻 FULL-STACK & DEVOPS\n* [Item 1]\n* [Item 2]\n\n"
        "---\n\n# 🔧 TOOLS & OPEN SOURCE\n* [Tool name]\n"
    )

    for i in range(retries):
        try:
            response = client.models.generate_content(model=model_id, contents=prompt)
            return response.text
        except Exception as e:
            if ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)) and i < retries - 1:
                print(f"⚠️ Quota hit. Retrying in 40s...")
                time.sleep(40)
            else: return f"AI Generation Failed: {e}"

def post_to_zoho(message):
    # .strip() removes any accidental spaces or hidden newline characters
    url = WEBHOOK_URL.strip() if WEBHOOK_URL else None
    
    if not url or not url.startswith("http"):
        print(f"❌ ERROR: Invalid Webhook URL format: {url}")
        return

    print("📤 Sending to Zoho Cliq...")
    try:
        # We use the cleaned 'url' variable here
        res = requests.post(url, json={"text": message}, timeout=15)
        res.raise_for_status()
        print("✅ Production Brief Delivered.")
    except Exception as e: 
        print(f"❌ Zoho Error: {e}")

if __name__ == "__main__":
    data = fetch_all_stack_news()
    if data:
        brief = generate_full_brief(data)
        print(f"\n--- PREVIEW ---\n{brief}\n---")
        post_to_zoho(brief)
