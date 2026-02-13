import os
import json
import requests
import time
from google import genai

# Configuration from GitHub Secrets
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
SERPER_KEY = os.getenv("SERPER_API_KEY")

def get_jobs():
    """Loosens the search to find more senior leads for the AI to filter."""
    # We remove the numeric "5..8" to avoid missing jobs where years aren't in the snippet.
    query = '("Senior Data Analyst" OR "Senior Data Engineer") (site:lever.co OR site:greenhouse.io OR site:jobs.ashbyhq.com)'
    
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, headers=headers, json={"q": query, "num": 100})
        results = response.json().get('organic', [])
        print(f"DEBUG: Serper found {len(results)} potential senior leads.")
        return results
    except Exception as e:
        print(f"ERROR: Search failed - {e}")
        return []

def analyze_jobs(jobs):
    """Uses Gemini to strictly filter for the 5-8 year sweet spot."""
    if not GEMINI_KEY:
        return []
        
    client = genai.Client(api_key=GEMINI_KEY)
    valid_jobs = []
    
    for j in jobs:
        role_title = j.get('title', '')
        snippet = j.get('snippet', '')
        
        prompt = f"""
        Analyze this job lead: {role_title} - {snippet}
        
        CRITERIA:
        1. Target experience: 5 to 9 years. 
        2. If the snippet doesn't mention years, but the title is "Senior" or "Staff", consider it a match.
        3. REJECT if it explicitly says "Junior", "Entry", "Intern", or "10+ years" / "Principal".
        
        If it's a match, return ONLY this JSON format: 
        {{"match": true, "exp": "5-8 Years", "co": "Company Name", "score": 95}}
        Otherwise, return {{"match": false}}
        """
        
        try:
            response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            clean_json = response.text.strip().replace('```json', '').replace('```', '').strip()
            data = json.loads(clean_json)
            
            if data.get('match') is True:
                valid_jobs.append({
                    "title": role_title,
                    "url": j.get('link'),
                    "company": data.get('co', 'Hiring Company'),
                    "experience": data.get('exp', '5-8 Years'),
                    "score": data.get('score', 90)
                })
            time.sleep(0.5) 
        except Exception:
            continue
            
    return valid_jobs

if __name__ == "__main__":
    print("🚀 Hunting for Senior Data Roles...")
    raw_leads = get_jobs()
    if raw_leads:
        final_list = analyze_jobs(raw_leads)
        with open('jobs.json', 'w') as f:
            json.dump(final_list, f, indent=4)
        print(f"✅ Mission Complete: Saved {len(final_list)} jobs.")
