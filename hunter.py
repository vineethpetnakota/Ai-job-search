import os
import json
import requests
import time
from google import genai

# Setup API Keys from GitHub Secrets
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
SERPER_KEY = os.getenv("SERPER_API_KEY")

def get_jobs():
    """Search for Analyst and Engineer roles across all company sizes"""
    # Expanded query to include Data Engineering and Enterprise portals (Workday, iCIMS, etc.)
    query = '("Data Analyst" OR "Data Engineer" OR "Data Engineering" OR "BI Engineer") "Remote" (site:myworkdayjobs.com OR site:icims.com OR site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com OR site:smartrecruiters.com OR site:workable.com)'
    
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json'}
    
    try:
        # Pulling 50 results to ensure a good mix of roles
        response = requests.post(url, headers=headers, json={"q": query, "num": 50})
        return response.json().get('organic', [])
    except Exception as e:
        print(f"Search failed: {e}")
        return []

def analyze_jobs(jobs):
    """Uses Gemini to score roles. Added a small delay to avoid rate limits."""
    if not GEMINI_KEY:
        print("Error: GEMINI_API_KEY missing.")
        return []
        
    client = genai.Client(api_key=GEMINI_KEY)
    valid_jobs = []
    
    for j in jobs:
        role_title = j.get('title', 'Unknown')
        snippet = j.get('snippet', '')
        link = j.get('link')

        # Refined prompt for more accurate categorization
        prompt = f"""
        Role: {role_title}
        Snippet: {snippet}
        Task: Is this a Data Analyst or Data Engineering role? 
        If yes, return ONLY JSON: {{"match": true, "score": 90, "co": "Company Name"}}. 
        If no, return: {{"match": false}}.
        """
        
        try:
            response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            # Clean JSON formatting
            clean_json = response.text.strip().replace('```json', '').replace('```', '').strip()
            data = json.loads(clean_json)
            
            if data.get('match') is True:
                valid_jobs.append({
                    "title": role_title,
                    "url": link,
                    "score": data.get('score', 85),
                    "company": data.get('co', 'Tech Company')
                })
            
            # Small 0.5s pause to respect API limits during larger crawls
            time.sleep(0.5)
            
        except Exception:
            continue
            
    return valid_jobs

if __name__ == "__main__":
    print("🚀 Starting Hunter...")
    raw_results = get_jobs()
    print(f"🔍 Found {len(raw_results)} potential leads across startups & enterprise.")
    
    final_matches = analyze_jobs(raw_results)
    
    with open('jobs.json', 'w') as f:
        json.dump(final_matches, f, indent=4)
        
    print(f"✅ Done! Saved {len(final_matches)} high-quality matches to jobs.json.")
