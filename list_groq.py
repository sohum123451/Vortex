import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv('.env')
client = Groq(api_key=os.getenv('GROQ_API_KEY'))
try:
    models = [m.id for m in client.models.list().data]
    print('Available Groq models:', models)
except Exception as e:
    print('Groq list error:', e)
