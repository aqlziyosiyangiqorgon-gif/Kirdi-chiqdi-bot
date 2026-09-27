from aiogram.fsm.state import State, StatesGroup

class AddAccountSG(StatesGroup):
    waiting_for_name = State()
    waiting_for_balance = State()

class AddCategorySG(StatesGroup):
    waiting_for_type = State()
    waiting_for_name = State()
    waiting_for_limit = State()
