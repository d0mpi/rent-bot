from aiogram.fsm.state import State, StatesGroup

class AdminAddState(StatesGroup):
    waiting_for_username = State()

class ListingState(StatesGroup):
    type = State()
    dynamic = State()