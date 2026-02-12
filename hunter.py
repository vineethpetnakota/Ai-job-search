import os
import json
import requests
from google import genai

# Setup API Keys from GitHub/Vercel Environment
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
SERPER_KEY = os.getenv("SERPER_API_KEY")

def get_jobs():
    """Hunts for job postings via Serper.dev"""
    query = '(site:*.lever.co | site:*.greenhouse.io | site:*.ashbyhq.com) ("Data Analyst" OR "BI Engineer" OR "Power BI") "Remote" after:2026-01-01'
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, headers=headers, json={"q": query, "num": 20})
        return response.json().get('organic', [])
    except Exception as e:
        print(f"Search failed: {e}")
        return []

def analyze_jobs(jobs):
    """Uses Gemini to score jobs based on your skills"""
    if not GEMINI_KEY:
        print("Error: GEMINI_API_KEY not found.")
        return []
        
    client = genai.Client(api_key=GEMINI_KEY)
    valid_jobs = []
    
    for j in jobs:
        role_title = j.get('title', 'Unknown Role')
        snippet = j.get('snippet', '')
        
        prompt = f"""
        Role: {role_title}
        Description: {snippet}
        
        Task: Is this a Data Analyst or BI role? 
        If yes, return ONLY JSON: {{"match": true, "score": 85, "co": "Company Name"}}
        If no, return ONLY JSON: {{"match": false}}
        """
        
        try:
            # New 2026 SDK Method
            response = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt
            )
            
            # Clean and parse the JSON response
            raw_text = response.text.strip().replace('```json', '').replace('```', '')
            data = json.loads(raw_text)
            
            if data.get('match'):
                valid_jobs.append({
                    "title": role_title,
                    "url": j.get('link'),
                    "score": data.get('score', 0),
                    "company": data.get('co', 'Startup')
                })
        except Exception as e:
            print(f"Skipping job due to error: {e}")
            continue
            
    return valid_jobs

if __name__ == "__main__":
    print("Starting job hunt...")
    found_jobs = get_jobs()
    print(f"Found {len(found_jobs)} potential links. Analyzing...")
    
    final_list = analyze_jobs(found_jobs)
    
    # Save results for the Vercel dashboard
    with open('jobs.json', 'w') as f:
        json.dump(final_list, f, indent=4)
    print(f"Successfully saved {len(final_list)} matched jobs to jobs.json")
