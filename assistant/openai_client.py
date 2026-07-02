import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def ask_openai(prompt: str, user_currency: str = 'INR') -> str:
    client = OpenAI(
        api_key=os.getenv('GROQ_API_KEY'), 
        base_url="https://api.groq.com/openai/v1"
    )
    
    system_prompt = (
        f"You are a professional financial advisor. Always provide all monetary values "
        f"specifically in {user_currency}. Be concise, accurate, and finance-focused. "
        f"Do not render graphs as text."
    )
    
    try:
        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"API Error: {str(e)}"