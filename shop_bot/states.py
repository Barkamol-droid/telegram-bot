from aiogram.fsm.state import State, StatesGroup


class OrderForm(StatesGroup):
    name = State()
    phone = State()
    address = State()
    comment = State()
    confirm = State()


class AddCategory(StatesGroup):
    name = State()


class AddProduct(StatesGroup):
    name = State()
    description = State()
    price = State()
    sizes = State()
    photo = State()


class Broadcast(StatesGroup):
    message = State()


class PromoForm(StatesGroup):
    percent = State()
    custom_period = State()
