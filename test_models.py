import os
from dotenv import load_dotenv
load_dotenv('.env')

# Test Gemini with gemini-3.6-flash and gemini-2.0-flash
from google import genai
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

for model in ['gemini-3.6-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']:
    try:
        res = client.models.generate_content(model=model, contents='Hi')
        print(f"Gemini ({model}): SUCCESS -> {res.text.strip()}")
        break
    except Exception as e:
        print(f"Gemini ({model}): FAILED -> {e}")

# Test Groq with various models
from groq import Groq
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
for model in ['llama-3.1-8b-instant', 'llama-3.1-70b-versatile', 'llama3-8b-8192', 'llama3-70b-8192', 'mixtral-8x7b-32768', 'gemma2-9b-it']:
    try:
        completion = groq_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi"}]
        )
        print(f"Groq ({model}): SUCCESS -> {completion.choices[0].message.content.strip()[:60]}")
    except Exception as e:
        print(f"Groq ({model}): FAILED -> {e}")
