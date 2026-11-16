import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

DEEPSEEK_API_KEY = "sk-d3358e073b1e46b0a8f8d28095adf708"
MODEL = "deepseek-chat"

user_histories = {}

def ask_deepseek(user_id, prompt):
    if not prompt.strip():
        return "Слушаю тебя. О чем хочешь спросить?"
        
    history = user_histories.get(user_id, [])
    history.append({"role": "user", "content": prompt})
    
    if len(history) > 6:
        history = history[-6:]

    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    messages = [
        {"role": "system", "content": "Ты голосовой ассистент в умной колонке. Отвечай на русском языке максимально кратко (1-2 предложения), без списков и звездочек."}
    ] + history

    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": 150,
        "temperature": 0.7,
        "stream": False
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=2.5)
        if resp.status_code != 200:
            return f"Ошибка API: {resp.status_code} - {resp.text[:50]}"
            
        data = resp.json()
        answer = data["choices"][0]["message"]["content"].strip()
        if not answer:
            return "Пустой ответ от модели."
            
        history.append({"role": "assistant", "content": answer})
        user_histories[user_id] = history
        return answer
    except requests.exceptions.Timeout:
        return "Сеть подтупливает, повтори вопрос."
    except Exception as e:
        return "Произошла ошибка связи."

@app.route("/", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return "Bot is active and running!", 200

    try:
        data = request.get_json(force=True, silent=True) or {}
        version = data.get("version", "1.0")
        session = data.get("session", {})
        user_id = session.get("user", {}).get("user_id", "default")
        command = data.get("request", {}).get("command", "")
        is_new_session = session.get("new", False)

        if is_new_session and not command:
            text = "Дипсик на связи. Спра
