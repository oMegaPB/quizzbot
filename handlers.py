import os
import re
import html
import logging
import pathlib

from aiogram import types, Router, Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.client.default import DefaultBotProperties

from models import Config

# поясню за type: ignore
# я устал бороться с аиограмом и тем 
# что нужно пихать бесконечное количество (почти) бесполезных ассертов
# лично мне удобнее закрыть на это глаза

router = Router(name="main")
config = Config.from_file("config.json")
properties = DefaultBotProperties(parse_mode="HTML")
bot = Bot(token=config.token, default=properties)

def get_logger(name: str, filename: str) -> logging.Logger:
    cwd = pathlib.Path(__file__).parent
    logger = logging.Logger(name=name)
    cwd.joinpath("logs").mkdir(exist_ok=True)
    handler = logging.FileHandler(cwd.joinpath("logs", filename), mode='a', encoding="u8", delay=False)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    return [logger.addHandler(handler), logger][1]

_log = get_logger("main", "log.log")

@router.startup()
async def on_startup(bot: Bot, dispatcher: Dispatcher, bots: tuple[Bot], router: Router):
    self = await bot.get_me()
    print(f"Logged in as {self.full_name}")
    print("All logs in ./logs/log.log")

@router.message(Command("start"))
async def start_handler(message: Message):
    if message.from_user:
        _log.info(f"{message.from_user.username} [{message.from_user.id}] just used /start")
    text = f"Добро пожаловать в <b>{config.team_name}</b>!\n\n"
    text += "Для начала подай заявку ⬇️"
    button = types.InlineKeyboardButton(text="💊 Подать заявку", callback_data="start")
    markup = types.InlineKeyboardMarkup(inline_keyboard=[[button]])
    await message.answer(text=text, reply_markup=markup)

@router.callback_query()
async def callback_query_handler(query: types.CallbackQuery, state: FSMContext):
    if query.data == "start":
        await state.set_state("on_questions")
        questions = iter(config.questions.items())
        key, question = next(questions)
        await state.set_data({"questions": questions, "question": key})
        await query.message.delete() # type: ignore
        await bot.send_message(query.message.chat.id, question) # type: ignore
    elif query.data in ["okay", "nah_wait"]: # user answers
        user = query.from_user
        _log.info(f"{user.username} [{user.id}] confirmed his answers. {query.data}")
        if query.data == "nah_wait":
            return await query.message.delete() # type: ignore
        answers = "\n".join(query.message.text.split("\n")[1:-2]) # type: ignore
        text = f"Заявка №<code>{os.urandom(4).hex()}</code>\n"
        if not query.from_user.username:
            name = html.escape(query.from_user.first_name)
            username = f"без юза. (<code>{name}</code>)"
        else:
            username = "<code>@" + html.escape(query.from_user.username) + "</code>"
        text += f"{username} <code>[{query.from_user.id}]</code>\n"
        answers = html.escape(answers)
        text += f"Ответы:\n{answers}"
        values = [["Принять ✅", "accept"], ["Отмена ❌", "deny"]]
        inline_keyboard = [[types.InlineKeyboardButton(text=x, callback_data=y)] for x, y in values]
        reply_markup = types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
        await bot.send_message(config.owner_accepter_id, text=text, reply_markup=reply_markup)
        await query.message.edit_text("Заявка отправлена ✅", reply_markup=None) # type: ignore
    elif query.data in ["accept", "deny"]: # admin answers
        user = query.from_user
        lines = query.message.text.split("\n") # type: ignore
        user_id = int(re.findall(r"\[(\d+)\]", lines[1])[0]) # вычленяем айдишник юзера
        _log.info(f"{user.username} [{user.id}] reviewed answers for {user_id}: {query.data}")
        rid = lines[0] # Заявка №{id}
        text = {
            "accept": f"Ваша заявка рассмотрена и принята. ✅\n\nЧат: {config.work_chat_url}",
            "deny": "Ваша заявка была отклонена ❌"
        }[query.data]
        await bot.send_message(user_id, text=text, disable_web_page_preview=True)
        await query.answer()
        action = 'отклонена ❌' if query.data == 'deny' else 'принята ✅'
        await bot.send_message(query.message.chat.id, rid + f" была {action}") # type: ignore

@router.message(StateFilter("on_questions"))
async def on_question(message: Message, state: FSMContext):
    if not message.text:
        return await message.reply("Ожидался ответ текстом. ❌")
    data = await state.get_data()
    answer = html.escape(message.text)
    await state.update_data({data["question"]: answer})
    questions = data["questions"]
    try:
        key, question = next(questions)
        await message.answer(question)
        await state.update_data({"question": key})
    except StopIteration:
        await state.clear()
        data[data["question"]] = answer
        answers = [y for x, y in data.items() if x not in ["questions", "question"]]
        parts = [f"{x}) {y}\n" for x, y in enumerate(answers, start=1)]
        text = "Ответы на вопросы:\n" + "".join(parts) + "\nВсе верно?"
        values = [["Все верно ✅", "okay"], ["Отмена ❌", "nah_wait"]]
        inline_keyboard = [[types.InlineKeyboardButton(text=x, callback_data=y)] for x, y in values]
        reply_markup = types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
        await bot.send_message(message.chat.id, text, reply_markup=reply_markup)
