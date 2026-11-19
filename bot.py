import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

API_KEY = os.environ.get("API_KEY", "").strip()
RAW_URL = os.environ.get("API_URL", "").strip()
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4o-mini").strip()

if RAW_URL and not RAW_URL.endswith("/chat/completions"):
    API_URL = RAW_URL.rstrip("/") + "/chat/completions"
else:
    API_URL = RAW_URL

user_histories = {}

def ask_llm(user_id, prompt):
    if not prompt.strip():
        return "Слушаю тебя. О чем хочешь спросить?"

    if not API_KEY or not API_URL:
        return "Не заданы API_KEY или API_URL в настройках сервера."

    history = user_histories.get(user_id, [])
    history.append({"role": "user", "content": prompt})

    if len(history) > 6:
        history = history[-6:]

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    messages = [
        {
            "role": "system",
            "content": "Ты голосовой ассистент в умной колонке. Отвечай на русском языке максимально кратко (1-2 предложения), без списков, звездочек и решеток."
        }
    ] + history

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "max_tokens": 150,
        "temperature": 0.7
    }

    try:
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=3.5)
        if resp.status_code != 200:
            return f"Ошибка шлюза {resp.status_code}: {resp.text[:70]}"

        data = resp.json()
        answer = data["choices"][0]["message"]["content"].strip()
        answer = answer.replace("*", "").replace("#", "")

        if not answer:
            return "Пустой ответ от модели."

        history.append({"role": "assistant", "content": answer})
        user_histories[user_id] = history
        return answer
    except requests.exceptions.Timeout:
        return "Нейросеть задумалась, повтори вопрос."
    except Exception as e:
        return f"Ошибка связи: {str(e)[:50]}"

@app.route("/", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return "Alice LLM Proxy Bot is running!", 200

    try:
        data = request.get_json(force=True, silent=True) or {}
        version = data.get("version", "1.0")
        session = data.get("session", {})
        user_id = session.get("user", {}).get("user_id", "default")
        command = data.get("request", {}).get("command", "")
        is_new_session = session.get("new", False)

        if is_new_session and not command:
            text = "Нейросеть на связи. Спрашивай!"
        elif command.lower() in ["хватит", "выход", "стоп", "пока"]:
            user_histories.pop(user_id, None)
            return jsonify({
                "version": version,
                "response": {"text": "До связи!", "end_session": True}
            })
        else:
            text = ask_llm(user_id, command)

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
