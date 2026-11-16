import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL_NAME = "gemini-1.5-flash"

user_histories = {}

def ask_gemini(user_id, prompt):
    if not prompt.strip():
        return "Слушаю тебя. О чем хочешь спросить?"
        
    history = user_histories.get(user_id, [])
    
    # Формируем историю для Gemini REST API (роли: user и model)
    gemini_contents = []
    for h in history:
        role = "user" if h["role"] == "user" else "model"
        gemini_contents.append({
            "role": role,
            "parts": [{"text": h["content"]}]
        })
    
    # Добавляем текущий запрос
    gemini_contents.append({
        "role": "user",
        "parts": [{"text": prompt}]
    })
    
    if len(gemini_contents) > 6:
        gemini_contents = gemini_contents[-6:]

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # Поддерживаем и Bearer-токены (AQ.), и обычные API-ключи
    params = {}
    if GEMINI_API_KEY.startswith("AQ.") or GEMINI_API_KEY.startswith("ya29."):
        headers["Authorization"] = f"Bearer {GEMINI_API_KEY}"
    else:
        params["key"] = GEMINI_API_KEY

    payload = {
        "contents": gemini_contents,
        "system_instruction": {
            "parts": [{"text": "Ты голосовой ассистент в умной колонке. Отвечай на русском языке максимально кратко (1-2 предложения), без списков и звездочек."}]
        },
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 150
        }
    }

    try:
        resp = requests.post(url, headers=headers, params=params, json=payload, timeout=5.0)
        if resp.status_code != 200:
            return f"Ошибка API: {resp.status_code} - {resp.text[:80]}"
            
        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return "Пустой ответ от модели."
            
        answer = candidates[0]["content"]["parts"][0]["text"].strip()
        if not answer:
            return "Пустой ответ от модели."
            
        # Сохраняем в историю
        history.append({"role": "user", "content": prompt})
        history.append({"role": "model", "content": answer})
        if len(history) > 6:
            history = history[-6:]
        user_histories[user_id] = history
        
        return answer
    except requests.exceptions.Timeout:
        return "Сеть подтупливает, повтори вопрос."
    except Exception as e:
        return f"Ошибка связи: {str(e)[:50]}"

@app.route("/", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return "Gemini Bot is active and running!", 200

    try:
        data = request.get_json(force=True, silent=True) or {}
        version = data.get("version", "1.0")
        session = data.get("session", {})
        user_id = session.get("user", {}).get("user_id", "default")
        command = data.get("request", {}).get("command", "")
        is_new_session = session.get("new", False)

        if is_new_session and not command:
            text = "Gemini на связи. Спрашивай!"
        elif command.lower() in ["хватит", "выход", "стоп", "пока"]:
            user_histories.pop(user_id, None)
            return jsonify({
                "version": version,
                "response": {"text": "До связи!", "end_session": True}
            })
        else:
            text = ask_gemini(user_id, command)

        return jsonify({
            "version": version,
            "response": {
                "text": text,
                "end_session": False
            }
        })
    except Exception:
        return jsonify({
            "version": "1.0",
            "response": {
                "text": "Ошибка обработки запроса.",
                "end_session": False
            }
        })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
