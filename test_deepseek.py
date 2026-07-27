import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Test DeepSeek API
api_key = os.getenv("DEEPSEEK_API_KEY")
print(f"Using API Key: {api_key[:10]}...")

try:
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1"
    )
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello in one sentence."}
        ],
        max_tokens=20
    )
    
    print("✅ DeepSeek API is working!")
    print(f"Response: {response.choices[0].message.content}")
    
except Exception as e:
    print(f"❌ Error: {e}")
