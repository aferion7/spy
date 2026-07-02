from groq import Groq
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

conversation_history = {}

SYSTEM_PROMPT = """Sen Farruhbekning shaxsiy assistantisan. Umarjon hozir band yoki yo'q.

Qoidalar:
- Xabar yozgan odamga Farruhbek tez orada javob berishini ayt
- Agar savol bo'lsa — savolni qabul qilib, Umarjon ko'rib javob berishini ayt
- Murojaat uchun rahmat ayt
- Qisqa va iltifotli bo'l
- O'zbek tilida yozishsa O'zbekcha, Ruscha yozishsa Ruscha, Inglizcha yozishsa Inglizcha javob ber
- Hech qachon "Men AI man" dema — oddiy assistant sifatida gapir

Misol javoblar:
- "Salom! xo'jayinim hozir band, tez orada javob beradi"
- "Xabaringiz uchun rahmat! Farruhbek ko'rib chiqadi va yaqin orada bog'lanadi"
- "Savol uchun rahmat, U bo'sh bo'lgach albatta javob beradi"
"""


def get_ai_reply(user_id: int, user_message: str) -> str:
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append({
        "role": "user",
        "content": user_message
    })

    if len(conversation_history[user_id]) > 20:
        conversation_history[user_id] = conversation_history[user_id][-20:]

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=500,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history[user_id]
        )
        reply = response.choices[0].message.content
