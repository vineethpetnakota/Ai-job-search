import os
import json
import requests
import time
from google import genai

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
SERPER_KEY = os.getenv("SERPER_API_KEY")

def get_jobs():
    """Broad search to ensure we get results."""
    # We use a very broad query. If it has 'Data' and 'Engineer' or 'Analyst', we want it.
    query = '("Data Analyst" OR "Data Engineer" OR "Business Intelligence Analyst") (site:lever.co OR site:greenhouse.io OR site:jobs.ashbyhq.com)'
    
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json'}
    
    try:
        # Requesting 100 results to give Gemini a huge pool
        response = requests.post(url, headers=headers, json={"q": query, "num": 100})
        results = response.json().get('organic', [])
        print(f"DEBUG: Serper found {len(results)} raw links.")
        return results
    except Exception as e:
        print(f"Search failed: {e}")
        return []

def analyze_jobs(jobs):
    if not GEMINI_KEY: return []
    client = genai.Client(api_key=GEMINI_KEY)
    valid_jobs = []
    
    for j in jobs:
        role_title = j.get('title', 'Unknown')
        snippet = j.get('snippet', '')
        
        # We tell Gemini: If it's a Data role, just give it to me. 
        # Don't be too strict about the 5 years if the snippet is short.
        prompt = f"""
        Role: {role_title}
        Snippet: {snippet}
        Is this a Data Analyst or Data Engineer role? 
        Answer ONLY in JSON: {{"match": true, "score": 90, "co": "Company Name"}}
        If it is totally unrelated (like Sales), {{"match": false}}.
        """
        
        try:
            response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            clean_json = response.text.strip().replace('```json', '').replace('```', '').strip()
            data = json.loads(clean_json)
            
            if data.get('match') is True:
                valid_jobs.append({
                    "title": role_title,
                    "url": j.get('link'),
                    "score": data.get('score', 85),
                    "company": data.get('co', 'Hiring Company')
                })
            time.sleep(0.2) 
        except:
            continue
            
    return valid_jobs

if __name__ == "__main__":
    raw_results = get_jobs()
    final_matches = analyze_jobs(raw_results)
    
    with open('jobs.json', 'w') as f:
        json.dump(final_matches, f, indent=4)
    print(f"✅ Saved {len(final_matches)} jobs.")
