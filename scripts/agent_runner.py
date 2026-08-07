import os
import json
from datetime import datetime
from pathlib import Path
import requests
from dotenv import load_dotenv

# Optional import for Google GenAI SDK
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# Force load .env from the root project directory
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


def log_agent_action(agent_name, prompt, response, duration):
    """Saves structured execution logs to .logs/agents/"""
    os.makedirs("./.logs/agents", exist_ok=True)
    log_file = f"./.logs/agents/{agent_name}.log"
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": agent_name,
        "prompt_length": len(prompt),
        "response_length": len(response),
        "duration_seconds": round(duration, 2),
        "response_snippet": response[:200] + "..." if len(response) > 200 else response
    }
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")


def call_local_ollama(prompt, model="qwen2.5-coder:7b"):
    """Delegates light coding/testing tasks to local RTX 3050 GPU."""
    start = datetime.now()
    ollama_host = os.getenv("OLLAMA_HOST") or "http://localhost:11434"
    url = f"{ollama_host}/api/generate"
    
    try:
        res = requests.post(
            url, 
            json={"model": model, "prompt": prompt, "stream": False}, 
            timeout=15
        )
        res_data = res.json()
        output = res_data.get("response", "")
        duration = (datetime.now() - start).total_seconds()
        
        log_agent_action("local_ollama_qwen7b", prompt, output, duration)
        return output
    except requests.exceptions.ConnectionError:
        return "ERROR: Could not connect to Ollama. Ensure 'ollama serve' is running on localhost:11434."
    except Exception as e:
        return f"Ollama Error: {str(e)}"


def call_groq_api(prompt, model="llama-3.1-8b-instant"):
    """Delegates fast code snippet tasks to Groq Cloud API."""
    start = datetime.now()
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key or api_key == "your_groq_api_key_here":
        return "WARNING: GROQ_API_KEY missing in .env file."
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10).json()
        output = res["choices"][0]["message"]["content"]
        duration = (datetime.now() - start).total_seconds()
        
        log_agent_action("cloud_groq", prompt, output, duration)
        return output
    except Exception as e:
        return f"Groq Error: {str(e)}"


def call_gemini_flash(prompt, model="gemini-3.6-flash"):
    """Delegates large-context tasks to Google AI Studio (Gemini Flash)."""
    start = datetime.now()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not GENAI_AVAILABLE:
        return "WARNING: 'google-genai' library not installed. Install via: pip install google-genai"
        
    if not api_key or api_key == "your_google_ai_studio_key_here":
        return "WARNING: GEMINI_API_KEY missing in .env file."
        
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )
        output = response.text
        duration = (datetime.now() - start).total_seconds()
        
        log_agent_action("cloud_gemini_flash", prompt, output, duration)
        return output
    except Exception as e:
        return f"Gemini Error: {str(e)}"


if __name__ == "__main__":
    print("🤖 Testing Agent Connections...")
    
    print("\n1. Testing Local Ollama (RTX 3050)...")
    ollama_res = call_local_ollama("Respond in one word: 'Ready'.")
    print("Result:", ollama_res.strip())
    
    print("\n2. Testing Groq Cloud API...")
    groq_res = call_groq_api("Respond in one word: 'Ready'.")
    print("Result:", groq_res.strip())
    
    print("\n3. Testing Google AI Studio (Gemini Flash)...")
    gemini_res = call_gemini_flash("Respond in one word: 'Ready'.")
    print("Result:", gemini_res.strip())
    
    print("\n✅ Execution complete. Check .logs/agents/ for output files.")