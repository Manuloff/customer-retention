import datetime
from pathlib import Path
from typing import List, Dict, Any

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, FSInputFile

from src.models import Contract, Offer
from src.repositories import Repositories
from src.services import DashboardScreenshotService

PAGE_SIZE = 10

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
STAT_PATH = ROOT_DIR / "stat.png"


class AdminStates(StatesGroup):
    MAIN_MENU = State()

    ENTITY_LIST = State()
    ENTITY_SELECTED = State()

    ENTITY_EDIT_WAIT_VALUE = State()

    ENTITY_CREATE_FILLING = State()


ENTITY_SCHEMAS = {
    "contract": {
        "fields": [
            # поля, доступные для редактирования (PK здесь исключён, т.к. репозиторий не поддерживает смену PK)
            "client_telegram_id",
            "last_name",
            "first_name",
            "middle_name",
            "email",
            "phone",
            "can_be_retained",
            "monthly_profit",
            "active",
        ],
        "create_fields": [
            # при создании все поля обязательны (включая contract_id)
            "contract_id",
            "client_telegram_id",
            "last_name",
            "first_name",
            "middle_name",
            "email",
            "phone",
            "can_be_retained",
            "monthly_profit",
            "active",
        ],
        "pk": "contract_id"
    },
    "offer": {
        "fields": [
            # offer_id нельзя редактировать
            "offer_type",
            "description",
            "min_profit_threshold",
            "cost",
        ],
        "create_fields": [
            "offer_type",
            "description",
            "min_profit_threshold",
            "cost",
        ],
        "pk": "offer_id"
    }
}

def admin_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📄 Контракты", callback_data="entity:list:contract:1"),
            InlineKeyboardButton(text="🎁 Офферы", callback_data="entity:list:offer:1"),
        ],
        [
            InlineKeyboardButton(text="🛑 Кейсы удержания", callback_data="retention:list:1"),
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
        ]
    ])

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def stats_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Ключевые показатели", callback_data="stat:kpi-indicators")],
        [InlineKeyboardButton(text="📊 Доходы и расходы по датам", callback_data="stat:revenue-expense-graph")],
        [InlineKeyboardButton(text="🍩 Распределение по типам удержания", callback_data="stat:pie-charts-block")],
        [InlineKeyboardButton(text="💰 Распределение прибыли", callback_data="stat:profit-histogram")],
        [InlineKeyboardButton(text="🔍 Корреляция прибыль/удержание", callback_data="stat:profit-retention-scatter")],
        [InlineKeyboardButton(text="🌐 Открыть дашборд", callback_data="stat:open-dashboard")],
    ])

def list_entities_keyboard(entity_type: str, items: List[Dict[str, Any]], page: int, total_pages: int) -> InlineKeyboardMarkup:
    kb_rows = []
    # кнопки для каждого элемента (кнопка текст = PK value)
    schema = ENTITY_SCHEMAS[entity_type]
    pk = schema["pk"]

    for it in items:
        # it может быть dict либо объект — приведём к строке id
        item_id = getattr(it, pk, None) if not isinstance(it, dict) else it.get(pk)
        kb_rows.append([InlineKeyboardButton(text=str(item_id), callback_data=f"entity:open:{entity_type}:{item_id}")])

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"entity:list:{entity_type}:{page-1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"entity:list:{entity_type}:{page+1}"))
    if nav:
        kb_rows.append(nav)

    # кнопки создания и назад
    kb_rows.append([
        InlineKeyboardButton(text="➕ Создать", callback_data=f"entity:create:{entity_type}"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")
    ])

    return InlineKeyboardMarkup(inline_keyboard=kb_rows)


def entity_edit_keyboard(entity_type: str) -> InlineKeyboardMarkup:
    schema = ENTITY_SCHEMAS[entity_type]
    field_buttons = []
    row = []
    for idx, field in enumerate(schema["fields"], start=1):
        row.append(InlineKeyboardButton(text=field, callback_data=f"entity:edit:{entity_type}:{field}"))
        # делаем по 2-3 кнопки в ряду для компактности
        if len(row) >= 2:
            field_buttons.append(row)
            row = []
    if row:
        field_buttons.append(row)

    # append delete and back
    field_buttons.append([
        InlineKeyboardButton(text="❌ Удалить", callback_data=f"entity:delete:{entity_type}"),
        InlineKeyboardButton(text="⬅️ Назад к списку", callback_data=f"entity:list:{entity_type}:1")
    ])
    return InlineKeyboardMarkup(inline_keyboard=field_buttons)

def get_entity_text(entity_type: str, ent) -> str:
    if entity_type == "contract":
        text = (
            f"*Контракт {getattr(ent, 'contract_id')}*\n\n"
            f"ID пользователя: `{getattr(ent, 'client_telegram_id')}`\n"
            f"Фамилия: `{getattr(ent, 'last_name')}`\n"
            f"Имя: `{getattr(ent, 'first_name')}`\n"
            f"Отчество: `{getattr(ent, 'middle_name')}`\n"
            f"Email: `{getattr(ent, 'email')}`\n"
            f"Телефон: `{getattr(ent, 'phone')}`\n\n"
            f"Можно удерживать: `{getattr(ent, 'can_be_retained')}`\n"
            f"Месячная прибыль: `{getattr(ent, 'monthly_profit')}`\n"
            f"Активен: `{getattr(ent, 'active')}`"
        )
    else:  # offer
        text = (
            f"*Оффер {getattr(ent, 'offer_id')}*\n\n"
            f"Тип: `{getattr(ent, 'offer_type')}`\n"
            f"Описание: `{getattr(ent, 'description')}`\n"
            f"Мин. порог профита: `{getattr(ent, 'min_profit_threshold')}`\n"
            f"Стоимость: `{getattr(ent, 'cost')}`"
        )

    return text


async def fetch_entity_by_id(repos: Repositories, entity_type: str, id_value: str):
    if entity_type == "contract":
        return await repos.contracts.get_one(id_value)
    elif entity_type == "offer":
        return await repos.offers.get_one(int(id_value))

    return None


def create_admin_router() -> Router:
    r = Router()

    @r.message(Command("admin"))
    async def admin_start(message: Message, state: FSMContext):
        await state.set_state(AdminStates.MAIN_MENU)
        await message.answer("🔐 *Админ-панель*\nВыберите раздел:", reply_markup=admin_main_menu())

    @r.callback_query(F.data == "admin_back")
    async def _back_to_main(callback: CallbackQuery, state: FSMContext):
        await state.set_state(AdminStates.MAIN_MENU)
        await callback.message.edit_text("🔐 *Админ-панель*\nВыберите раздел:", reply_markup=admin_main_menu())


    # Получить список с энтити entity:list:<entity_type>:<page>
    @r.callback_query(F.data.startswith("entity:list:"))
    async def entity_list(callback: CallbackQuery, state: FSMContext, repos: Repositories):
        # parse
        try:
            _, _, entity_type, page_str = callback.data.split(":")
            page = int(page_str)
        except Exception:
            await callback.answer("Неверный формат", show_alert=True)
            return

        if entity_type not in ENTITY_SCHEMAS:
            await callback.answer("Неизвестная сущность", show_alert=True)
            return

        async with repos.database:
            if entity_type == "contract":
                all_items = await repos.contracts.get_all()
            else:
                all_items = await repos.offers.get_all()

        if not all_items:
            await callback.message.edit_text("Список пуст.")
            return

        total_pages = (len(all_items) - 1) // PAGE_SIZE + 1
        page = max(1, min(page, total_pages))
        start = (page - 1) * PAGE_SIZE
        end = start + PAGE_SIZE
        slice_items = all_items[start:end]

        # сохраняем в состояние только список ID (не объекты целиком)
        pk = ENTITY_SCHEMAS[entity_type]["pk"]
        id_list = [str(getattr(it, pk)) for it in all_items]
        await state.update_data(entity_type=entity_type, entity_id_list=id_list, entity_page=page)

        await callback.message.edit_text(
            f"📄 *Список {entity_type}s* — страница {page}/{total_pages}",
            reply_markup=list_entities_keyboard(entity_type, slice_items, page, total_pages)
        )

    # Открыть элемент: entity:open:<entity_type>:<id>
    @r.callback_query(F.data.startswith("entity:open:"))
    async def entity_open(callback: CallbackQuery, state: FSMContext, repos: Repositories):
        try:
            _, _, entity_type, id_value = callback.data.split(":")
        except Exception:
            await callback.answer("Неверный формат", show_alert=True)
            return

        if entity_type not in ENTITY_SCHEMAS:
            await callback.answer("Неизвестная сущность", show_alert=True)
            return

        async with repos.database:
            ent = await fetch_entity_by_id(repos, entity_type, id_value)

        if ent is None:
            await callback.answer("Элемент не найден", show_alert=True)
            return

        # Сохраняем текущий выбор
        await state.update_data(selected_entity_type=entity_type, selected_entity_id=str(id_value))
        await state.set_state(AdminStates.ENTITY_SELECTED)

        # Сформируем текст подробно

        await callback.message.edit_text(get_entity_text(entity_type, ent), reply_markup=entity_edit_keyboard(entity_type))

    # Нажали редактировать поле: entity:edit:<entity_type>:<field>
    @r.callback_query(F.data.startswith("entity:edit:"))
    async def entity_edit_field(callback: CallbackQuery, state: FSMContext):
        try:
            _, _, entity_type, field = callback.data.split(":")
        except Exception:
            await callback.answer("Неверный формат", show_alert=True)
            return

        # сохраняем поле и переводим состояние
        await state.update_data(edit_field=field)
        await state.set_state(AdminStates.ENTITY_EDIT_WAIT_VALUE)

        await callback.message.edit_text(f"Введите новое значение для поля *{field}*:")

    # Получили новое значение для поля
    @r.message(AdminStates.ENTITY_EDIT_WAIT_VALUE)
    async def apply_entity_edit(message: Message, state: FSMContext, repos: Repositories):
        data = await state.get_data()
        entity_type = data.get("selected_entity_type")
        entity_id = data.get("selected_entity_id")
        field = data.get("edit_field")

        if not entity_type or not entity_id or not field:
            await message.answer("Сессия прервана. Повторите действие.")
            await state.clear()
            return

        # типизация входных данных
        raw = message.text.strip()
        new_value: Any = raw
        # приведение типов по полю
        if field in ("client_telegram_id",):
            try:
                new_value = int(raw)
            except Exception:
                await message.answer("Ожидалось целое число.")
                return
        elif field in ("monthly_profit", "min_profit_threshold", "cost"):
            try:
                new_value = float(raw)
            except Exception:
                await message.answer("Ожидалось число.")
                return
        elif field in ("can_be_retained", "active"):
            new_value = raw.lower() in ("1", "да", "true", "yes", "y")

        # Получаем сущность
        async with repos.database:
            ent = await fetch_entity_by_id(repos, entity_type, entity_id)

            if ent is None:
                await message.answer("Элемент исчез.")
                await state.clear()
                return

            # обновляем атрибут
            setattr(ent, field, new_value)

            # Сохраняем через репозиторий
            if entity_type == "contract":
                await repos.contracts.update(ent)
            else:  # offer
                await repos.offers.update(ent)

        await message.answer("✔ Поле обновлено.")

        async with repos.database:
            ent = await fetch_entity_by_id(repos, str(entity_type), entity_id)


        await message.answer(get_entity_text(str(entity_type), ent), reply_markup=entity_edit_keyboard(str(entity_type)))
        await state.set_state(AdminStates.ENTITY_SELECTED)

    # Удаление сущности: entity:delete:<entity_type>
    @r.callback_query(F.data.startswith("entity:delete:"))
    async def entity_delete(callback: CallbackQuery, state: FSMContext, repos: Repositories):
        try:
            _, _, entity_type = callback.data.split(":")
        except Exception:
            await callback.answer("Неверный формат", show_alert=True)
            return

        data = await state.get_data()
        entity_id = data.get("selected_entity_id")
        if not entity_id:
            await callback.answer("Сессия прервана", show_alert=True)
            return

        async with repos.database:
            if entity_type == "contract":
                # в ContractRepository нет метода remove — используем прямой запрос
                await repos.contracts.remove(int(entity_id))
            else:
                await repos.offers.remove(int(entity_id))

        await callback.message.edit_text("🗑 Удалено.")
        await state.set_state(AdminStates.MAIN_MENU)
        await callback.message.answer("Главное меню:", reply_markup=admin_main_menu())

    # Создание сущности: entity:create:<entity_type>
    @r.callback_query(F.data.startswith("entity:create:"))
    async def entity_create_start(callback: CallbackQuery, state: FSMContext):
        try:
            _, _, entity_type = callback.data.split(":")
        except Exception:
            await callback.answer("Неверный формат", show_alert=True)
            return

        if entity_type not in ENTITY_SCHEMAS:
            await callback.answer("Неизвестная сущность", show_alert=True)
            return

        await state.set_state(AdminStates.ENTITY_CREATE_FILLING)
        await state.update_data(create_entity_type=entity_type, create_index=0, create_data={})

        first_field = ENTITY_SCHEMAS[entity_type]["create_fields"][0]
        await callback.message.edit_text(f"Создание {entity_type} — введите значение для поля *{first_field}*:")

    @r.message(AdminStates.ENTITY_CREATE_FILLING)
    async def entity_create_collect(message: Message, state: FSMContext, repos: Repositories):
        data = await state.get_data()
        entity_type = data.get("create_entity_type")
        index = data.get("create_index", 0)
        collected = data.get("create_data", {})

        if not entity_type:
            await message.answer("Сессия прервана.")
            await state.clear()
            return

        field = ENTITY_SCHEMAS[entity_type]["create_fields"][index]
        raw = message.text.strip()

        # приведение типов
        if field in ("client_telegram_id",):
            try:
                value = int(raw)
            except Exception:
                await message.answer("Ожидалось целое число.")
                return
        elif field in ("monthly_profit", "min_profit_threshold", "cost"):
            try:
                value = float(raw)
            except Exception:
                await message.answer("Ожидалось число.")
                return

        elif field in ("can_be_retained", "active"):
            value = raw.lower() in ("1", "да", "true", "yes", "y")
        else:
            value = raw

        collected[field] = value
        index += 1

        # если есть ещё поля — запрашиваем следующий
        if index < len(ENTITY_SCHEMAS[entity_type]["create_fields"]):
            await state.update_data(create_index=index, create_data=collected)
            next_field = ENTITY_SCHEMAS[entity_type]["create_fields"][index]
            await message.answer(f"Введите значение для поля *{next_field}*:")
            return

        # всё собрано — создаём сущность
        async with repos.database:
            if entity_type == "contract":
                # Порядок: contract_id, client_telegram_id, last_name, first_name, middle_name, email, phone, can_be_retained, monthly_profit, active
                new_contract = Contract(
                    collected["contract_id"],
                    collected["client_telegram_id"],
                    collected.get("last_name"),
                    collected.get("first_name"),
                    collected.get("middle_name"),
                    collected.get("email"),
                    collected.get("phone"),
                    bool(collected.get("can_be_retained", False)),
                    float(collected.get("monthly_profit", 0.0)),
                    bool(collected.get("active", True))
                )
                await repos.contracts.insert(new_contract)
                await message.answer("✔ Контракт создан.")
            else:  # offer
                # создаём Offer(0, offer_type, description, min_profit_threshold, cost)
                new_offer = Offer(
                    0,
                    collected.get("offer_type"),
                    collected.get("description"),
                    float(collected.get("min_profit_threshold", 0.0)),
                    float(collected.get("cost", 0.0))
                )
                await repos.offers.insert(new_offer)
                await message.answer("✔ Оффер создан.")

        await state.set_state(AdminStates.MAIN_MENU)
        await message.answer("Главное меню:", reply_markup=admin_main_menu())

    # Список кейсов: retention:list:<page>
    @r.callback_query(F.data.startswith("retention:list:"))
    async def retention_list(callback: CallbackQuery, state: FSMContext, repos: Repositories):
        _, _, page_str = callback.data.split(":")
        page = int(page_str)

        async with repos.database:
            cases = await repos.cases.get_all_escalated()

        if not cases:
            await callback.message.edit_text("Список кейсов удержания пуст.")
            return

        total_pages = (len(cases) - 1) // PAGE_SIZE + 1
        page = max(1, min(page, total_pages))

        start = (page - 1) * PAGE_SIZE
        end = start + PAGE_SIZE
        slice_ = cases[start:end]

        kb = []
        for case in slice_:
            kb.append([
                InlineKeyboardButton(
                    text=f"{case.case_id} | {case.contract_id}",
                    callback_data=f"retention:open:{case.case_id}"
                )
            ])

        nav = []
        if page > 1:
            nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"retention:list:{page - 1}"))
        if page < total_pages:
            nav.append(InlineKeyboardButton(text="➡️", callback_data=f"retention:list:{page + 1}"))
        if nav:
            kb.append(nav)

        kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")])

        await callback.message.edit_text(
            f"*Кейсы удержания — страница {page}/{total_pages}*",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

        await state.update_data(retention_list=cases, retention_page=page)

    # Открытие конкретного кейса: retention:open:<id>
    @r.callback_query(F.data.startswith("retention:open:"))
    async def retention_open(callback: CallbackQuery, state: FSMContext, repos: Repositories):
        _, _, cid = callback.data.split(":")

        async with repos.database:
            case = await repos.cases.get_one(cid)
            if not case:
                await callback.answer("Кейс не найден", show_alert=True)
                return

            contract = await repos.contracts.get_one(case.contract_id)

        await state.update_data(current_retention_id=cid)

        # Текст максимально подробный
        text = (
            f"*Кейс удержания #{case.case_id}*\n\n"
            f"Контракт: `{case.contract_id}`\n"
            f"Причина: `{case.initial_reason}`\n"
            f"Статус: `{case.status}`\n"
            f"Создан: `{case.created_at}`\n\n"
        )

        if contract:
            text += (
                "*Информация по контракту:*\n"
                f"ID: `{contract.client_telegram_id}`\n"
                f"Фамилия: `{contract.last_name}`\n"
                f"Имя: `{contract.first_name}`\n"
                f"Отчество: `{contract.middle_name}`\n"
                f"Email: `{contract.email}`\n"
                f"Телефон: `{contract.phone}`\n"
                f"Активен: `{contract.active}`\n"
                f"Месячный профит: `{contract.monthly_profit}`\n"
            )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Клиент остался", callback_data="retention:resolve:stay"),
                InlineKeyboardButton(text="🔴 Клиент ушёл", callback_data="retention:resolve:left"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data=f"retention:list:1")
            ]
        ])

        await callback.message.edit_text(text, reply_markup=kb)

    # Завершение кейса: retention:resolve:<stay|left>
    @r.callback_query(F.data.startswith("retention:resolve:"))
    async def retention_resolve(callback: CallbackQuery, state: FSMContext, repos: Repositories):
        _, _, decision = callback.data.split(":")

        data = await state.get_data()
        cid = data.get("current_retention_id")
        if not cid:
            await callback.answer("Ошибка состояния", show_alert=True)
            return

        async with repos.database:
            case = await repos.cases.get_one(cid)
            if not case:
                await callback.answer("Кейс не найден", show_alert=True)
                return

            case.completed_at = datetime.datetime.now()
            case.status = "retained" if decision == "stay" else "churned"
            await repos.cases.update(case)

            if decision == 'left':
                contract = await repos.contracts.get_one(case.contract_id)
                contract.active = False

                await repos.contracts.update(contract)

        await callback.message.edit_text(
            "✔ Кейс успешно обновлён.\nВозврат в меню.",
        )
        await state.set_state(AdminStates.MAIN_MENU)
        await callback.message.answer("Главное меню:", reply_markup=admin_main_menu())

    @r.callback_query(F.data == 'stats')
    async def admin_statistics(callback: CallbackQuery, state: FSMContext):
        await callback.message.edit_text(
            "Выберите нужный блок статистики:",
            reply_markup=stats_keyboard()
        )

    @r.callback_query(F.data.startswith("stat:"))
    async def stats_block_selected(callback: CallbackQuery, state: FSMContext, screenshot_service: DashboardScreenshotService):
        action = callback.data.split(":")[1]

        await callback.answer()  # закрыть "часики"
        await callback.message.edit_text("⏳ Формирую, подождите...")

        if action == "open-dashboard":
            await callback.message.answer("Страница дашборда: https://your-dash-url/")
            return

        try:
            await screenshot_service.screenshot_graph(action, str(STAT_PATH))

            await callback.message.answer_photo(
                photo=FSInputFile(STAT_PATH)
            )

            await callback.message.answer("Выберите следующий график:", reply_markup=stats_keyboard())

        except Exception as e:
            print("Ошибка при получении скриншота", e)
            await callback.message.answer(f"Ошибка при получении скриншота")

    return r
