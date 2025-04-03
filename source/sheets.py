import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import CREDENTIALS_PATH, SHEET_NAME

def load_params_from_sheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    values = sheet.get_all_values()
    params_tree = {}
    for row in values[1:]:
        housing_type, param, options = row[0], row[1], row[2]
        if housing_type not in params_tree:
            params_tree[housing_type] = []
        params_tree[housing_type].append((param, options.split(',') if options else []))
    return params_tree

PARAMS_TREE = load_params_from_sheets()