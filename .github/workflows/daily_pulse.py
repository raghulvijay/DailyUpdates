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

    # A. Search Hacker News for TOP Tech Trends (>100 points)
    # This captures the most important tech story regardless of keyword
    try:
        hn_url = f"https://hn.algolia.com/api/v1/search?tags=story&numericFilters=created_at_i>{y_unix},points>100"
        hn_res = requests.get(hn_url, timeout=10).json()
        for hit in hn_res.get('hits', [])[:8]:
            news_buffer.append(f"[Trending] {hit['title']} (URL: {hit.get('url')})")
    except Exception as e: print(f"⚠️ HN Error: {e}")

    # B. Global News with Broad Tech Stack Query
    try:
        # Broad query covering AI, Web, Mobile, DevOps, and Backend
        broad_query = (
            "Artificial Intelligence OR LLM OR Cybersecurity OR "
            "ReactJS OR Angular OR Node.js OR Python OR GoLang OR "
            "DevOps OR Kubernetes OR Cloud Computing OR Open Source"
        )
        url = f"https://newsdata.io/api/1/news?apikey={NEWS_DATA_KEY}&q={broad_query}&language=en&from_date={y_date}"
        res = requests.get(url, timeout=15).json()
        articles = res.get('results', [])
        
        if articles:
            # Logic to handle varying list lengths safely
            count = min(len(articles), 12) 
            for i in range(count):
                news_buffer.append(f"[News] {articles[i]['title']} (Source: {articles[i].get('source_id')})")
    except Exception as e: print(f"⚠️ NewsData Error: {e}")

    return "\n".join(news_buffer)

def generate_full_brief(raw_content, retries=3):
    print("🧠 Gemini Deep Dive: Analyzing All-Stack Trends...")
    
    model_id = "gemini-2.5-flash-lite"
    search_tool = types.Tool(google_search=types.GoogleSearch())
    
    prompt = (
        f"You are a Senior Technical Architect. Analyze these updates from the last 24h:\n{raw_content}\n\n"
        "Instructions:\n"
        "1. Identify the 1 most critical AI update.\n"
        "2. Identify the 3 most important tech updates.\n"
        "3. Format specifically for Zoho Cliq Markdown.\n\n"
        "CRITICAL FORMATTING RULES:\n"
        "- Use '#' for Main Titles.\n"
        "- Use '---' for horizontal separators.\n"
        "- Use '**' for bold text.\n"
        "- Use TWO newlines between every section.\n\n"
        "STRUCTURE:\n"
        "# 🚀 TOP AI DEEP-DIVE | {yesterday_str}\n"
        "**[Title]**\n"
        "*Impact*: [2 sentences]\n\n"
        "---\n\n"
        "# 🤖 AI & MACHINE LEARNING\n"
        "* [Item 1]\n"
        "* [Item 2]\n\n"
        "---\n\n"
        "# 💻 FULL-STACK & DEVOPS\n"
        "* [Item 1]\n"
        "* [Item 2]\n"
        "* [Item 3]\n\n"
        "---\n\n"
        "# 🔧 TOOLS & OPEN SOURCE\n"
        "* [Interesting tool/repo]\n"
    )

    for i in range(retries):
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(tools=[search_tool])
            )
            return response.text
        except Exception as e:
            if "429" in str(e) and i < retries - 1:
                time.sleep((i + 1) * 30)
            else: return f"AI Generation Failed: {e}"

def post_to_zoho(message):
    print("📤 Sending to Zoho Cliq...")
    try:
        requests.post(WEBHOOK_URL, json={"text": message}, timeout=10)
        print("✅ Production Brief Delivered.")
    except Exception as e: print(f"❌ Zoho Error: {e}")

if __name__ == "__main__":
    data = fetch_all_stack_news()
    if data:
        brief = generate_full_brief(data)
        print(f"\n--- PREVIEW ---\n{brief}\n---")
        post_to_zoho(brief)
