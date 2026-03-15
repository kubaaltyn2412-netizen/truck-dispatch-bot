import os
import anthropic
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# === СИСТЕМНЫЕ ПРОМПТЫ ===
SYSTEM_PROMPTS = {
    "load": """Ты профессиональный AI-агент для трак диспетчера. Помогаешь находить выгодные грузы (loads) на load boards (DAT, Truckstop, 123Loadboard).
Знаешь всё о типах грузов: dry van, reefer, flatbed, step deck, RGN, lowboy, tanker, hazmat, oversized.
Помогаешь анализировать load postings, считать RPM, определять выгодные направления, deadhead miles.
Отвечай на русском, технические термины оставляй на английском. Будь конкретным и полезным.""",

    "rate": """Ты эксперт по расчёту рейтов в трак диспетчинге (США).
Помогаешь считать: RPM, fuel surcharge, accessorial charges, detention pay, TONU, layover pay.
Знаешь средние рейты по направлениям, как торговаться с брокерами.
Умеешь считать gross revenue, net profit, fuel cost, dispatcher commission (8-12%).
Отвечай на русском, цифры и термины на английском.""",

    "broker": """Ты коуч по переговорам для трак диспетчера. Знаешь психологию работы с брокерами (Coyote, Echo, CH Robinson, TQL, Uber Freight).
Помогаешь вести переговоры по рейту, отвечать на низкие предложения, составлять email и call скрипты.
Знаешь тактики: counter offer, market rate leverage, relationship building.
Скрипты пиши на английском, объяснения на русском.""",

    "docs": """Ты эксперт по документации в американском трак бизнесе.
Знаешь все документы: BOL, Rate Confirmation, POD, Invoice, Carrier Packet, W-9, Certificate of Insurance, MC Authority, IFTA, IRP, ELD logs.
Объясняешь что заполнять, как читать документы, типичные ошибки.
Отвечай на русском, названия документов на английском.""",

    "hos": """Ты эксперт по HOS (Hours of Service) правилам FMCSA для CMV в США.
Знаешь все правила: 11-hour driving limit, 14-hour on-duty window, 30-minute break rule, 60/70-hour limits, 34-hour restart, sleeper berth, short-haul exemption.
Знаешь ELD requirements, violations и как их избежать.
Объясняешь просто, даёшь примеры расчёта часов. Отвечай на русском.""",

    "fmcsa": """Ты эксперт по FMCSA и DOT регуляциям в США.
Знаешь: MC number, DOT number, safety ratings, CSA scores, roadside inspections, drug & alcohol testing, insurance requirements, cargo insurance.
Знаешь state-specific правила, permit requirements для OD/OW loads, HAZMAT regulations.
Отвечай на русском, аббревиатуры на английском.""",

    "general": """Ты опытный трак диспетчер и коуч с глубокими знаниями американской транспортной индустрии.
Знаешь всё: load boards, брокеры, owner-operators, fleet management, factoring companies, fuel cards (EFS, Comdata), truck stops, scales, TWIC, HAZMAT, oversize, detention, accessorials.
Отвечаешь на любые вопросы по трак диспетчингу, помогаешь решать проблемы.
Общаешься на русском, технические термины на английском."""
}

# Хранилище режимов пользователей
user_modes = {}

# === КЛАВИАТУРА ===
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("📦 Найти груз"), KeyboardButton("💵 Расчёт рейта")],
        [KeyboardButton("🤝 Брокер / переговоры"), KeyboardButton("📄 Документы / BOL")],
        [KeyboardButton("⏱️ HOS правила"), KeyboardButton("⚖️ FMCSA / DOT")],
        [KeyboardButton("💬 Свободный чат")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# === ХЭНДЛЕРЫ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_modes[update.effective_user.id] = "general"
    await update.message.reply_text(
        "🚛 *Truck Dispatch AI — твой персональный агент!*\n\n"
        "Я знаю всё про трак диспетчинг:\n"
        "• Load boards и поиск грузов\n"
        "• Расчёт рейтов и прибыли\n"
        "• Переговоры с брокерами\n"
        "• BOL, Rate Con, документы\n"
        "• HOS правила и ELD\n"
        "• FMCSA / DOT регуляции\n\n"
        "Выбери режим или задай вопрос! 👇",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # Определяем режим по кнопкам
    mode_map = {
        "📦 Найти груз": "load",
        "💵 Расчёт рейта": "rate",
        "🤝 Брокер / переговоры": "broker",
        "📄 Документы / BOL": "docs",
        "⏱️ HOS правила": "hos",
        "⚖️ FMCSA / DOT": "fmcsa",
        "💬 Свободный чат": "general"
    }

    if text in mode_map:
        user_modes[user_id] = mode_map[text]
        mode_names = {
            "load": "📦 Режим: Поиск грузов\nВставь load posting или опиши что ищешь.",
            "rate": "💵 Режим: Расчёт рейта\nВведи данные: откуда → куда, мили, рейт.",
            "broker": "🤝 Режим: Переговоры с брокерами\nОпиши ситуацию или попроси скрипт.",
            "docs": "📄 Режим: Документы\nЗадай вопрос по BOL, Rate Con, Invoice и др.",
            "hos": "⏱️ Режим: HOS правила\nЗадай вопрос по часам вождения.",
            "fmcsa": "⚖️ Режим: FMCSA / DOT\nЗадай вопрос по регуляциям.",
            "general": "💬 Свободный чат\nЗадай любой вопрос про трак индустрию."
        }
        await update.message.reply_text(mode_names[user_modes[user_id]])
        return

    # Получаем текущий режим
    current_mode = user_modes.get(user_id, "general")
    system_prompt = SYSTEM_PROMPTS[current_mode]

    # Показываем что печатаем
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=system_prompt,
            messages=[{"role": "user", "content": text}]
        )
        reply = response.content[0].text
        # Telegram лимит 4096 символов
        if len(reply) > 4000:
            reply = reply[:4000] + "\n\n..._(продолжение — уточни вопрос)_"
        await update.message.reply_text(reply, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text("⚠️ Ошибка. Попробуй ещё раз.")

# === ЗАПУСК ===
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🚛 Truck Dispatch Bot запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
