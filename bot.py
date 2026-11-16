import os
import google.generativeai as genai
from flask import Flask, request, jsonify

app = Flask(__name__)

# Читаем ключ Gemini из переменных окружения Render
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-1.5-flash"

generation_config = {
    "temperature": 0.7,
    "max_output_tokens": 150,
}
system_instruction = "Ты голосовой ассистент в умной колонке. Отвечай на русском языке максимально кратко (1-2 предложения), без списков и звездочек."

model = genai.GenerativeModel(
    model_name=MODEL_NAME,
    generation_config=generation_config,
    system_instruction=system_instruction
)

user_chats = {}

def ask_gemini(user_id, prompt):
    if not prompt.strip():
        return "Слушаю тебя. О чем хочешь спросить?"
    
    try:
        if user_id not in user_chats:
            user_chats[user_id] = model.start_chat(history=[])
        
        chat = user_chats[user_id]
        response = chat.send_message(prompt)
        answer = response.text.strip()
        
        if not answer:
            return "Пустой ответ от модели."
        return answer
    except Exception as e:
        return f"Ошибка Gemini: {str(e)[:60]}"

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
            user_chats.pop(user_id, None)
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
