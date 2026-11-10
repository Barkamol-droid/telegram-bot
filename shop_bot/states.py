from aiogram.fsm.state import State, StatesGroup


class OrderForm(StatesGroup):
    name = State()
    phone = State()
    address = State()
    confirm = State()


class AddCategory(StatesGroup):
    name = State()


class AddProduct(StatesGroup):
    name = State()
    description = State()
    price = State()
    photo = State()


class Broadcast(StatesGroup):
    message = State()
