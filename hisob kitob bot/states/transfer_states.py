from aiogram.fsm.state import State, StatesGroup

class TransferSG(StatesGroup):
    waiting_for_source_account = State()
    waiting_for_target_account = State()
    waiting_for_amount = State()
