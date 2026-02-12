import os
import json
import requests
from google import genai

# Setup API Keys
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
SERPER_KEY = os.getenv("SERPER_API_KEY")

def get_jobs():
    """Search for a wider range of roles to ensure results"""
    # Broadened query: Removed strict date limit and added more job titles
    query = '(site:lever.co OR site:greenhouse.io OR site:ashbyhq.com) ("Data Analyst" OR "Business Intelligence" OR "Data Analytics") "Remote"'
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, headers=headers, json={"q": query, "num": 25})
        return response.json().get('organic', [])
    except Exception as e:
        print(f"Search failed: {e}")
        return []

def analyze_jobs(jobs):
    """Uses Gemini to score jobs. Modified to be more 'forgiving' to get results."""
    if not GEMINI_KEY:
        print("Error: GEMINI_API_KEY missing.")
        return []
        
    client = genai.Client(api_key=GEMINI_KEY)
    valid_jobs = []
    
    for j in jobs:
        role_title = j.get('title', 'Unknown')
        snippet = j.get('snippet', '')
        link = j.get('link')

        prompt = f"Role: {role_title}\nSnippet: {snippet}\nTask: Is this a Data/BI role? If yes, return ONLY JSON: {{\"match\": true, \"score\": 90, \"co\": \"Company Name\"}}. If no, return: {{\"match\": false}}."
        
        try:
            response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            # Clean potential Markdown formatting from AI response
            clean_json = response.text.strip().replace('```json', '').replace('```', '').strip()
            data = json.loads(clean_json)
            
            if data.get('match') is True:
                valid_jobs.append({
                    "title": role_title,
                    "url": link,
                    "score": data.get('score', 80),
                    "company": data.get('co', 'Tech Company')
                })
        except:
            continue
            
    return valid_jobs

if __name__ == "__main__":
    print("Hunting...")
    raw_results = get_jobs()
    print(f"Found {len(raw_results)} potential leads.")
    
    final_matches = analyze_jobs(raw_results)
    
    with open('jobs.json', 'w') as f:
        json.dump(final_matches, f, indent=4)
    print(f"Done! Saved {len(final_matches)} jobs.")
