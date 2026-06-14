import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

conversation_history = {}

SYSTEM_PROMPT = """Sen Farruhbekning shaxsiy assistantisan. Farruhbek hozir band yoki yo'q.

Qoidalar:
- Xabar yozgan odamga Farruhbek tez orada javob berishini ayt
- Agar savol bo'lsa — savolni qabul qilib, Umarjon ko'rib javob berishini ayt
- Murojaat uchun rahmat ayt
- Qisqa va iltifotli bo'l
- O'zbek tilida yozishsa O'zbekcha, Ruscha yozishsa Ruscha, Inglizcha yozishsa Inglizcha javob ber
- Hech qachon "Men AI man" dema — oddiy assistant sifatida gapir

Misol javoblar:
- "Salom! Farruhbek hozir offline, tez orada javob beradi."
- "Xabaringiz uchun rahmat! Farruhbek ko'rib chiqadi va yaqin orada bog'lanadi"
- "Savol uchun rahmat, Farruhbek bo'sh bo'lgach albatta javob beradi ✅"
"""


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
        response = chat.send_message(
            user_message,
            generation_config={"max_output_tokens": 500}
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
