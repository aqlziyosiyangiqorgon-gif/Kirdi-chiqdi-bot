from aiogram.fsm.state import State, StatesGroup

class TransactionSG(StatesGroup):
    waiting_for_category = State()
    waiting_for_account = State()
    waiting_for_amount = State()
    waiting_for_comment = State()
