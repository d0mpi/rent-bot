# states.py
from aiogram.fsm.state import State, StatesGroup

class ReferralState(StatesGroup):
    waiting_for_description_create = State()
    waiting_for_description_edit = State()

class AdminAddState(StatesGroup):
    waiting_for_username = State()

class ListingState(StatesGroup):
    step = State()

class SearchState(StatesGroup):
    step = State()

class EditState(StatesGroup):
    step = State()

class RequestState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_district = State()
    waiting_for_date = State()
    waiting_for_comment = State()