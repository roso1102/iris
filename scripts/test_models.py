import sys
from vertexai.generative_models import GenerativeModel
from vertexai import init

init(project='naturepivot-rag', location='us-central1')

names = [
    'gemini-3.6-flash',
    'gemini-3.5-flash',
    'gemini-3.5-flash-lite',
    'gemini-1.5-flash',
    'gemini-2.0-flash',
]

for name in names:
    try:
        m = GenerativeModel(name)
        r = m.generate_content('Say hello', generation_config={'max_output_tokens': 10})
        print(f'OK: {name} -> {r.text.strip()[:50]}', flush=True)
    except Exception as e:
        msg = str(e)
        if '404' in msg or 'NOT_FOUND' in msg or 'not found' in msg.lower() or 'access' in msg.lower():
            print(f'NOT FOUND: {name}', flush=True)
        else:
            print(f'OTHER ERROR: {name} -> {msg[:120]}', flush=True)
