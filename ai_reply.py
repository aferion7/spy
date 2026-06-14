import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

conversation_history = {}

SYSTEM_PROMPT = """Sen do'stona va qisqa javob beruvchi Telegram assistantsan.
O'zbek tilida yozishsa O'zbekcha, Ruscha yozishsa Ruscha, Inglizcha yozishsa Inglizcha javob ber.
Javoblar qisqa va tabiiy bo'lsin — xuddi oddiy odam kabi."""


def get_ai_reply(user_id: int, user_message: str) -> str:
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append({
        "role": "user",
        "parts": [user_message]
    })

    if len(conversation_history[user_id]) > 20:
        conversation_history[user_id] = conversation_history[user_id][-20:]

    try:
        chat = model.start_chat(history=conversation_history[user_id][:-1])
        response = chat.send_message(user_message, 
            generation_config={"max_output_tokens": 500},
            system_instruction=SYSTEM_PROMPT
        )
        reply = response.text

        conversation_history[user_id].append({
            "role": "model",
            "parts": [reply]
        })
        return reply
    except Exception as e:
        return f"Xatolik: {e}"


def clear_history(user_id: int):
    conversation_history.pop(user_id, None)
