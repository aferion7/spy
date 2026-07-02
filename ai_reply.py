from groq import Groq
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

conversation_history = {}

SYSTEM_PROMPT = """Sen Farruhbekning shaxsiy assistantisan. Farruhbek hozir band yoki yoq.

Qoidalar:
- Xabar yozgan odamga Farruhbek tez orada javob berishini ayt
- Agar savol bolsa savolni qabul qilib Umarjon korib javob berishini ayt
- Murojaat uchun rahmat ayt
- Qisqa va iltifotli bol
- Ozbek tilida yozishsa Ozbekcha Ruscha yozishsa Ruscha Inglizcha yozishsa Inglizcha javob ber
- Hech qachon Men AI man dema oddiy assistant sifatida gapir
"""


def get_ai_reply(user_id, user_message):
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append({
        "role": "user",
        "content": user_message
    })

    if len(conversation_history[user_id]) > 20:
        conversation_history[user_id] = conversation_history[user_id][-20:]

    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history[user_id]
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=500,
            messages=messages
        )
        reply = response.choices[0].message.content
        conversation_history[user_id].append({
            "role": "assistant",
            "content": reply
        })
        return reply
    except Exception as e:
        return "Xatolik: " + str(e)


def clear_history(user_id):
    conversation_history.pop(user_id, None)
