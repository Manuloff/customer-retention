import datetime
from random import choice

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, \
    CallbackQuery

from src.models import RetentionCase
from src.repositories import Repositories


class States(StatesGroup):
    MAIN_MENU = State()
    WAITING_FOR_REASON = State()
    OFFER_DECISION = State()

def create_client_router():
    r = Router()

    # Без группы

    @r.message(Command("start"))
    async def command_start(message: Message, state: FSMContext):
        print("on start")

        await state.clear()
        await state.set_state(States.MAIN_MENU)

        await message.answer(
            "👋 **Добро пожаловать!** Выберите действие в меню ниже",
            reply_markup=ReplyKeyboardMarkup(keyboard=[
                [KeyboardButton(text="Посмотреть мой договор")],
                [KeyboardButton(text="Отказаться от услуг")]
            ], resize_keyboard=True)
        )

    # Главное меню

    @r.message(F.text == "Посмотреть мой договор")
    async def view_contract(message: Message, state: FSMContext, repos: Repositories):
        async with repos.database:
            contract = await repos.contracts.get_by_client_telegram_id(message.from_user.id)

            if contract is None:
                await message.answer("❌ Активный контракт не найден. Пожалуйста, убедитесь, что ваш Telegram ID связан с контрактом")
                return

            await message.answer(
                f"📝 **Информация о вашем контракте**\n"
                f"**ID Контракта:** `{contract.contract_id}`\n"
                f"**Заключен с:** `{contract.last_name + " " + contract.first_name + " " + contract.middle_name}`\n"
                f"**Электронный адрес**: `{contract.email}`\n"
                f"**Номер телефона:** `{contract.phone}`\n"
                f"**Статус:** `{"Активен" if contract.active else "Не активен"}`"
            )

    @r.message(F.text == "Отказаться от услуг")
    async def init_churn(message: Message, state: FSMContext, repos: Repositories):
        async with repos.database:
            contract = await repos.contracts.get_by_client_telegram_id(message.from_user.id)

            if contract is None:
                await message.answer("❌ Активный контракт не найден. Пожалуйста, убедитесь, что ваш Telegram ID связан с контрактом")
                return

            if not contract.active:
                await message.answer("❌ Ваш контракт неактивен")
                return

            active_case = await repos.cases.get_active_case_for_contract(contract.contract_id)
            if active_case:
                await message.answer("⚠️ У вас уже есть активный кейс удержания")
                return

            await state.update_data(contract_id=contract.contract_id)
            await state.set_state(States.WAITING_FOR_REASON)

            await message.answer(
                "Пожалуйста, укажите **краткую причину**, по которой вы хотите расторгнуть договор",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Пропустить причину", callback_data="skip_reason")]
                ])
            )

    # Ввод причины отказа от услуг

    @r.message(States.WAITING_FOR_REASON)
    async def process_reason(message: Message, state: FSMContext, repos: Repositories):
        reason = message.text

        await create_case_and_send_offer(message, state, repos, reason)

    @r.callback_query(F.data == 'skip_reason')
    async def skip_reason(callback: CallbackQuery, state: FSMContext, repos: Repositories):
        await callback.message.edit_text(
            f"{callback.message.text}\n\n*Причина: не указана*",
            reply_markup=None
        )

        await create_case_and_send_offer(callback.message, state, repos, "Не указано (через бота)")

    async def create_case_and_send_offer(message: Message, state: FSMContext, repos: Repositories, reason):
        async with repos.database:
            contract_id = (await state.get_data()).get("contract_id")

            await state.clear()

            if not contract_id:
                await message.answer("Ошибка сессии. Начните с команды /start")
                return

            contract = await repos.contracts.get_one(contract_id)
            if not contract:
                await message.answer("Ваш контракт не найден, попробуйте ещё раз")
                return

            # Подбираем предложение для клиента
            offers = await repos.offers.get_suitable_offers(contract.monthly_profit)

            # Доступных офферов нет или запрет на удержание, кейс можно сразу закрыть как "клиент ушел"
            if not offers or not contract.can_be_retained:
                await state.clear()

                case = RetentionCase(
                    0,
                    contract_id,
                    reason,
                    None,
                    None,
                    datetime.datetime.now(),
                    datetime.datetime.now(),
                    'churned'
                )

                await repos.cases.insert(case)

                contract.active = False
                await repos.contracts.update(contract)

                await message.answer("Ваш договор отозван")
                return

            # С помощью рандома выберем случайный оффер если их несколько
            offer = choice(offers)

            case_id = await repos.cases.insert(RetentionCase(
                0,
                contract_id,
                reason,
                offer.offer_id,
                None,
                datetime.datetime.now(),
                None,
                'active'
            ))

            await state.update_data(case_id=case_id)
            await state.set_state(States.OFFER_DECISION)

            await message.answer(
                f"Мы бы хотели сохранить вас в качестве своего клиента,"
                f" поэтому готовы предоставить вам **{offer.offer_type}** на сумму **{offer.cost:.2f}**\n\n"
                "Подробности предложения:\n"
                f"{offer.description}\n\n"
                "Вы согласны принять это предложение?",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Согласиться", callback_data=f"accept")],
                    [InlineKeyboardButton(text="❌ Отказаться", callback_data=f"decline")]
                ])
            )

    @r.callback_query(States.OFFER_DECISION)
    async def process_offer_decision(callback: CallbackQuery, state: FSMContext, repos: Repositories):
        async with repos.database:
            case_id = (await state.get_data()).get("case_id")
            await state.clear()

            if not case_id:
                await callback.message.answer("Ошибка сессии. Начните с команды /start")
                return

            case = await repos.cases.get_one(case_id)
            if not case:
                await callback.message.answer("Ваш кейс не найден, попробуйте ещё раз")
                return

            action = callback.data

            if action == 'accept':
                case.completed_at = datetime.datetime.now()
                case.status = 'retained'

                await callback.message.edit_text(
                    "**✅ Предложение принято!**\n\n"
                    "Изменения вступят в силу в ближайшее время!\n"
                    "Спасибо, что остаетесь с нами!",
                    reply_markup=None
                )

            elif action == 'decline':
                # Получаем список с "свободными" админами, чтобы произвести эскалацию к старшему
                admins = await repos.users.get_free_admins()

                if admins:
                    # Выбираем случайного админа
                    admin = choice(admins)

                    case.status = 'escalated'
                    case.assigned_manager_id = admin.telegram_id

                    await callback.bot.send_message(
                        admin.telegram_id,
                        f"⚠️ *Новая заявка на удержание*\n\n"
                        f"Клиент: `{callback.from_user.full_name}`\n"
                        f"ID клиента: `{callback.from_user.id}`\n"
                        f"Причина отказа: `{case.initial_reason}`\n"
                        f"ID кейса: `{case.case_id}`\n"
                        f"Контракт ID: `{case.contract_id}`"
                    )

                    await callback.message.edit_text(
                        "**❌ Предложение отклонено**\n\n"
                        "Ваша заявка на отзыв договора отправлена старшему сотруднику.\n"
                        "Плата за услуги временно приостановлена до принятия решения",
                        reply_markup=None
                    )

                else:
                    case.status = 'churned'
                    case.completed_at = datetime.datetime.now()

                    await callback.message.edit_text(
                        "**❌ Предложение отклонено**\n\n"
                        "Ваша заявка принята, договор больше недействителен\n"
                        "Очень надеемся, что вы в скором времени к нам вернетесь!",
                        reply_markup=None
                    )

            else:
                await callback.message.edit_text("Неизвестное действие", reply_markup=None)
                return

            await repos.cases.update(case)

    return r