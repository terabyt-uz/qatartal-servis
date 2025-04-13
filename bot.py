
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from datetime import datetime
import openpyxl
import os

TOKEN = '8157133012:AAHORdzEolkcF9HAuybnVes9YtDiitCJqVA'
ADMIN_CHAT_ID = 1087968824  # ← Замени на свой Telegram ID

user_states = {}
user_problem_types = {}
user_descriptions = {}

def save_to_excel(user, problem_type, description):
    file_name = 'заявки.xlsx'
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if not os.path.exists(file_name):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Заявки"
        ws.append(['Дата и время', 'Имя пользователя', 'Тип проблемы', 'Описание'])
        wb.save(file_name)
    wb = openpyxl.load_workbook(file_name)
    ws = wb.active
    ws.append([now, user, problem_type, description])
    wb.save(file_name)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton("🔧 Оставить заявку", callback_data='new_request')],
        [InlineKeyboardButton("📞 Контакты", callback_data='contacts')],
        [InlineKeyboardButton("ℹ️ Частые вопросы", callback_data='faq')],
        [InlineKeyboardButton("👁 Узнать мой Chat ID", callback_data='get_chat_id')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = (
    f"👋 Добро пожаловать в ЖЭК-бот!\n\n"
    f"🆔 Ваш Telegram ID: `{user_id}`"
)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id  # ← вот ЭТО должно быть

    if query.data == 'new_request':
        keyboard = [
            [InlineKeyboardButton("💡 Свет", callback_data='type_💡 Свет'),
             InlineKeyboardButton("🚰 Вода", callback_data='type_🚰 Вода')],
            [InlineKeyboardButton("🔥 Отопление", callback_data='type_🔥 Отопление'),
             InlineKeyboardButton("🧹 Уборка", callback_data='type_🧹 Уборка')],
            [InlineKeyboardButton("📦 Другое", callback_data='type_📦 Другое')],
        ]
        await query.edit_message_text("Выберите тип проблемы:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'get_chat_id':
        chat_id = query.message.chat_id
        await query.edit_message_text(f"🆔 Ваш Telegram ID: `{chat_id}`", parse_mode="Markdown")

    elif query.data.startswith('type_'):
        problem_type = query.data.replace('type_', '')
        user_problem_types[user_id] = problem_type
        user_states[user_id] = 'awaiting_description'
        await query.message.reply_text(f"✍️ Опишите, пожалуйста, проблему по теме: {problem_type.lower()}")

    elif query.data == 'confirm':
        user_id = query.from_user.id
        username = query.from_user.username or query.from_user.full_name
        problem_type = user_problem_types.get(user_id)
        description = user_descriptions.get(user_id)

        if not problem_type or not description:
            await context.bot.send_message(chat_id=user_id, text="⚠️ Заявка не найдена.")
            return

        save_to_excel(username, problem_type, description)

        msg = f"""📩 Заявка от @{username}:
🔧 Тип: {problem_type}
📄 Описание: {description}"""

        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg)
        print("⏳ Отправляю сообщение пользователю…")
        await context.bot.send_message(chat_id=user_id, text="✅ Ваша заявка принята! Спасибо.")

        # Очистка данных
        user_states.pop(user_id, None)
        user_problem_types.pop(user_id, None)
        user_descriptions.pop(user_id, None)

    elif query.data == 'cancel':
        await query.edit_message_text("❌ Заявка отменена.")
        user_states.pop(user_id, None)
        user_problem_types.pop(user_id, None)
        user_descriptions.pop(user_id, None)

    elif query.data == 'contacts':
        await query.edit_message_text(
            "📞 Диспетчерская: +998 93 578 60 92, +998 90 990 38 44\n"
            "🏢 Адрес: квартал 6, дом 31, кв. 38\n"
            "🕒 Работаем: с 9:00 до 21:00"
        )

    elif query.data == 'faq':
        await query.edit_message_text(
            "🔹 Отопление включается с 15 октября\n"
            "🔹 Протечка? Сообщите здесь или по телефону диспетчера"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    message_text = update.message.text

    if user_states.get(user_id) == 'awaiting_description':
        user_descriptions[user_id] = message_text
        problem_type = user_problem_types.get(user_id)
        description = message_text

        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data='confirm')],
            [InlineKeyboardButton("❌ Отменить", callback_data='cancel')]
        ]
        text = f"""📋 Ваша заявка:
🔧 Тип: {problem_type}
📄 Описание: {description}

Подтвердите отправку:"""
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(
    "❗ Сначала нажмите кнопку 'Оставить заявку' и выберите тип проблемы.\n"
    "Затем вы сможете ввести описание."
)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🚀 Бот с инлайн-кнопками запущен!")
    app.run_polling()

if __name__ == '__main__':
    main()
