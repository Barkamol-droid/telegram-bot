from aiogram.fsm.state import State, StatesGroup


class OrderForm(StatesGroup):
    name = State()
    phone = State()
    address = State()
    comment = State()
    bonus = State()
    confirm = State()


class AddCategory(StatesGroup):
    name = State()


class AddProduct(StatesGroup):
    name = State()
    description = State()
    price = State()
    sizes = State()
    photo = State()
    video = State()


class Broadcast(StatesGroup):
    message = State()


class AdminForm(StatesGroup):
    user = State()


class PromoForm(StatesGroup):
    percent = State()
    custom_period = State()


class BonusSend(StatesGroup):
    recipient = State()
    amount = State()


class EditMedia(StatesGroup):
    wait = State()
