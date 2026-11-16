import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

GEMINI_API_KEY = "AQ.Ab8RN6KfkjxR7WKt90lTSkji0I3umUB9j2dd5it5mjplvQX0mg"
MODEL = "gemini-1.5-flash"

user_histories = {}

def ask_gemini(user_id, prompt):
    if not prompt.strip():
        return "Слушаю тебя. О чем хочешь спросить?"
        
    history = user_histories.get(user_id, [])
    history.append({"role": "user", "parts": [{"text": prompt}]})
    
    if len(history) > 4:
        history = history[-4:]

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY
    }
    
    payload = {
        "systemInstruction": {
            "parts": [{
                "text": "Ты голосовой ассистент Gemini в умной колонке. Отвечай на русском языке максимально кратко (1-2 предложения), без списков и звездочек."
            }]
        },
        "contents": history,
        "generationConfig": {
            "maxOutputTokens": 150,
            "temperature": 0.7
        }
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=2.5)
        
        if resp.status_code != 200:
            return f"Ошибка API: {resp.status_code}"
            
        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates or "content" not in candidates[0]:
            return "Пустой ответ от модели."
            
        answer = candidates[0]["content"].get("parts", [{}])[0].get("text", "").strip()
        if not answer:
            return "Не удалось получить текст ответа."
            
        history.append({"role": "model", "parts": [{"text": answer}]})
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
