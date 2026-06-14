message_cache = {}

def save_message(chat_id, msg_id, data):
    message_cache[(chat_id, msg_id)] = data

def get_message(chat_id, msg_id):
    return message_cache.get((chat_id, msg_id))

def delete_from_cache(chat_id, msg_id):
    return message_cache.pop((chat_id, msg_id), None)
