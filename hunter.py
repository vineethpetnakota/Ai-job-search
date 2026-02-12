import os, json, requests
from google import genai

# Setup
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
SERPER_KEY = os.getenv("SERPER_API_KEY")

def get_jobs():
    query = '(site:*.lever.co | site:*.greenhouse.io | site:*.ashbyhq.com) ("Data Analyst" OR "BI Engineer" OR "Power BI" OR "Data Engineer") "Remote" after:2026-01-01'
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers, data=json.dumps({"q": query, "num": 20}))
    return response.json().get('organic', [])

def analyze_jobs(jobs):
    client = genai.Client(api_key=GEMINI_KEY)
    valid_jobs = []
    for j in jobs:
        prompt = f"Role: {j['title']}. Is this a Data Analyst, BI, or Data Engineering role? If yes, return JSON: {{\"match\": true, \"score\": 0-100, \"co\": \"Company\"}}. If no: {{\"match\": false}}."
        try:
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            data = json.loads(res.text.strip('`json\n '))
            if data.get('match'):
                valid_jobs.append({"title": j['title'], "url": j['link'], "score": data['score'], "company": data['co']})
        except: continue
    return valid_jobs

if __name__ == "__main__":
    found = get_jobs()
    final = analyze_jobs(found)
    with open('jobs.json', 'w') as f:
        json.dump(final, f, indent=4)
