
import os
import time
import requests
import anthropic

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

SYSTEM_PROMPTS = {
    "load": "Ты профессиональный AI-агент для трак диспетчера. Помогаешь находить выгодные грузы на load boards (DAT, Truckstop). Знаешь dry van, reefer, flatbed, RPM, deadhead miles. Отвечай на русском, термины на английском.",
    "rate": "Ты эксперт по расчёту рейтов в трак диспетчинге США. Считаешь RPM, fuel surcharge, detention pay, dispatcher fee (8-12%), net profit. Отвечай на русском, цифры на английском.",
    "broker": "Ты коуч по переговорам с брокерами (CH Robinson, TQL, Coyote). Помогаешь с counter offer, скриптами звонков, emails. Скрипты на английском, объяснения на русском.",
    "docs": "Ты эксперт по документации в трак бизнесе. Знаешь BOL, Rate Confirmation, POD, Invoice, Carrier Packet, W-9. Отвечай на русском, названия документов на английском.",
    "hos": "Ты эксперт по HOS правилам FMCSA. Знаешь 11/14 hour rule, 34-hour restart, sleeper berth, ELD. Объясняй просто на русском.",
    "fmcsa": "Ты эксперт по FMCSA и DOT. Знаешь MC/DOT numbers, CSA scores, safety ratings, insurance requirements. Отвечай на русском.",
    "general": "Ты опытный трак диспетчер. Знаешь всё: load boards, брокеры, owner-operators, factoring, fuel cards, HAZMAT, oversize. Отвечай на русском, термины на английском.",
}

user_modes = {}

KEYBOARDS = {
    "main": {
        "keyboard": [
            ["📦 Найти груз", "💵 Расчёт рейта"],
            ["🤝 Брокер", "📄 Документы / BOL"],
            ["⏱️ HOS правила", "⚖️ FMCSA / DOT"],
            ["💬 Свободный чат"]
        ],
        "resize_keyboard": True
    }
}

MODE_MAP = {
    "📦 Найти груз": "load",
    "💵 Расчёт рейта": "rate",
    "🤝 Брокер": "broker",
    "📄 Документы / BOL": "docs",
    "⏱️ HOS правила": "hos",
    "⚖️ FMCSA / DOT": "fmcsa",
    "💬 Свободный чат": "general",
}

MODE_NAMES = {
    "load": "📦 Режим: Поиск грузов\nВставь load posting или опиши что ищешь.",
    "rate": "💵 Режим: Расчёт рейта\nВведи данные: откуда → куда, мили, рейт.",
    "broker": "🤝 Режим: Переговоры с брокерами\nОпиши ситуацию или попроси скрипт.",
    "docs": "📄 Режим: Документы\nЗадай вопрос по BOL, Rate Con, Invoice.",
    "hos": "⏱️ Режим: HOS правила\nЗадай вопрос по часам вождения.",
    "fmcsa": "⚖️ Режим: FMCSA / DOT\nЗадай вопрос по регуляциям.",
    "general": "💬 Свободный чат\nЗадай любой вопрос про трак индустрию.",
}

def send_message(chat_id, text, reply_markup=None):
    import json
    data = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{BASE_URL}/sendMessage", data=data)

def send_typing(chat_id):
    requests.post(f"{BASE_URL}/sendChatAction", data={"chat_id": chat_id, "action": "typing"})

def get_updates(offset=None):
    params = {"timeout": 30, "offset": offset}
    try:
        r = requests.get(f"{BASE_URL}/getUpdates", params=params, timeout=35)
        return r.json().get("result", [])
    except:
        return []

def ask_claude(system, user_text):
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=system,
            messages=[{"role": "user", "content": user_text}]
        )
        return response.content[0].text
    except Exception as e:
        return f"Ошибка: {str(e)}"

def handle_update(update):
    message = update.get("message")
    if not message:
        return
    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    if text == "/start":
        user_modes[chat_id] = "general"
        send_message(chat_id,
            "Truck Dispatch AI — твой персональный агент!\n\n"
            "Я знаю всё про трак диспетчинг:\n"
            "• Load boards и поиск грузов\n"
            "• Расчёт рейтов и прибыли\n"
            "• Переговоры с брокерами\n"
            "• BOL, Rate Con, документы\n"
            "• HOS правила и ELD\n"
            "• FMCSA / DOT регуляции\n\n"
            "Выбери режим или задай вопрос!",
            reply_markup=KEYBOARDS["main"]
        )
        return

    if text in MODE_MAP:
        user_modes[chat_id] = MODE_MAP[text]
        send_message(chat_id, MODE_NAMES[user_modes[chat_id]])
        return

    mode = user_modes.get(chat_id, "general")
    send_typing(chat_id)
    reply = ask_claude(SYSTEM_PROMPTS[mode], text)
    if len(reply) > 4000:
        reply = reply[:4000] + "\n\n...уточни вопрос для продолжения"
    send_message(chat_id, reply)

def main():
    print("Truck Dispatch Bot запущен!")
    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates:
            try:
                handle_update(update)
            except Exception as e:
                print(f"Ошибка: {e}")
            offset = update["update_id"] + 1
        time.sleep(0.5)

if __name__ == "__main__":
    main()
