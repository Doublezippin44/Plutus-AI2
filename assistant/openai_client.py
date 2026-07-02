import os
from openai import OpenAI
from dotenv import load_dotenv

# Load variables from the .env file
load_dotenv()

def ask_openai(prompt: str) -> str:
    # Read the key from the environment
    api_key = os.getenv('GOOGLE_API_KEY')
    
    client = OpenAI(
        api_key=api_key, 
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    
    
    try:
        response = client.chat.completions.create(
            model='gemini-1.5-pro',
            messages=[
                {"role": "system", "content": "You are a financial advisor."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"API Error: {str(e)}"