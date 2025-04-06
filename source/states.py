from aiogram.fsm.state import State, StatesGroup

class AdminAddState(StatesGroup):
    waiting_for_username = State()

class ListingState(StatesGroup):
    step = State()

class SearchState(StatesGroup):
    step = State()

class EditState(StatesGroup):
    step = State()