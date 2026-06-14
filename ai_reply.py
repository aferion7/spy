import anthropic

client = anthropic.Anthropic()

conversation_history = {}

SYSTEM_PROMPT = """Sen do'stona va qisqa javob beruvchi Telegram assistantsan.
O'zbek tilida yozishsa O'zbekcha, Ruscha yozishsa Ruscha, Inglizcha yozishsa Inglizcha javob ber.
Javoblar qisqa va tabiiy bo'lsin — xuddi oddiy odam kabi."""


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
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=conversation_history[user_id]
        )
        reply = response.content[0].text
        conversation_history[user_id].append({
            "role": "assistant",
            "content": reply
        })
        return reply
    except Exception as e:
        return f"Xatolik: {e}"


def clear_history(user_id: int):
    conversation_history.pop(user_id, None)
