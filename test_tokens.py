import os, asyncio
from dotenv import load_dotenv
load_dotenv('.env')

results = {}

# 1. Gemini test
try:
    from google import genai
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents='Say hello in one word'
    )
    results["Gemini"] = {"valid": True, "response": response.text.strip()}
except Exception as e:
    results["Gemini"] = {"valid": False, "error": str(e)}

# 2. Groq test
try:
    from groq import Groq
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    completion = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "Say hello in one word"}]
    )
    results["Groq"] = {"valid": True, "response": completion.choices[0].message.content.strip()}
except Exception as e:
    results["Groq"] = {"valid": False, "error": str(e)}

# 3. CricAPI test
try:
    import urllib.request, json
    cric_key = os.getenv('CRICAPI_KEY')
    req = urllib.request.Request(f'https://api.cricapi.com/v1/currentMatches?apikey={cric_key}&offset=0', headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        results["CricAPI"] = {"valid": data.get("status") == "success", "matches_found": len(data.get("data", []))}
except Exception as e:
    results["CricAPI"] = {"valid": False, "error": str(e)}

# 4. Discord token check
try:
    import urllib.request, json
    req = urllib.request.Request(
        'https://discord.com/api/v10/users/@me',
        headers={'Authorization': f'Bot {os.getenv("DISCORD_TOKEN")}', 'User-Agent': 'DiscordBot (https://discord.com, 1.0)'}
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        results["Discord"] = {"valid": True, "bot_username": f"{data.get('username')}#{data.get('discriminator', '0')}"}
except Exception as e:
    results["Discord"] = {"valid": False, "error": str(e)}

import json
print(json.dumps(results, indent=2))
