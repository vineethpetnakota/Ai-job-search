import os
import json
import requests
import time
from google import genai

# Configuration from GitHub Secrets
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
SERPER_KEY = os.getenv("SERPER_API_KEY")

def get_jobs():
    """Fetches up to 100 job leads from major ATS platforms."""
    # Broadening the search: Removed "Remote" to include Hybrid/Onsite.
    # Added 'Senior' and 'Lead' to prioritize 5+ year roles.
    query = '("Senior Data Analyst" OR "Senior Data Engineer" OR "Lead Data Engineer") (site:lever.co OR site:greenhouse.io OR site:jobs.ashbyhq.com OR site:workable.com)'
    
    url = "https://google.serper.dev/search"
    headers = {
        'X-API-KEY': SERPER_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(url, headers=headers, json={"q": query, "num": 100})
        results = response.json().get('organic', [])
        print(f"DEBUG: Serper found {len(results)} raw links.")
        return results
    except Exception as e:
        print(f"ERROR: Search failed - {e}")
        return []

def analyze_jobs(jobs):
    """Uses Gemini to filter roles based on seniority and relevance."""
    if not GEMINI_KEY:
        print("ERROR: GEMINI_API_KEY is missing.")
        return []
        
    client = genai.Client(api_key=GEMINI_KEY)
    valid_jobs = []
    
    for j in jobs:
        role_title = j.get('title', 'Unknown Role')
        snippet = j.get('snippet', '')
        link = j.get('link')

        # We ask Gemini to look for 5+ years, but we are lenient with snippets.
        prompt = f"""
        Role: {role_title}
        Company Info: {snippet}
        
        Task: Is this a Senior/Lead Data Analyst or Data Engineering role? 
        Criteria: Ideally requires 5+ years of experience.
        
        Return ONLY valid JSON:
        {{"match": true, "score": 95, "co": "Actual Company Name"}}
        
        If it's entry-level or unrelated, return:
        {{"match": false}}
        """
        
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt
            )
            
            # Cleaning the AI response for pure JSON
            raw_text = response.text.strip()
            clean_json = raw_text.replace('```json', '').replace('```', '').strip()
            data = json.loads(clean_json)
            
            if data.get('match') is True:
                valid_jobs.append({
                    "title": role_title,
                    "url": link,
                    "score": data.get('score', 90),
                    "company": data.get('co', 'Hiring Company')
                })
            
            # Respect Rate Limits (Free tier)
            time.sleep(0.5)
            
        except Exception as e:
            # Skip errors silently to keep the loop moving
            continue
            
    return valid_jobs

if __name__ == "__main__":
    print("🚀 Starting the Senior Data Job Hunter...")
    
    # 1. Fetch
    raw_leads = get_jobs()
    
    # 2. Filter
    if raw_leads:
        final_list = analyze_jobs(raw_leads)
        
        # 3. Save
        with open('jobs.json', 'w') as f:
            json.dump(final_list, f, indent=4)
        
        print(f"✅ Success: Saved {len(final_list)} jobs to jobs.json.")
    else:
        print("⚠️ No leads found by Serper. Check your API key or Query.")
