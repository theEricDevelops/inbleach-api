import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_DIR = os.path.join(ROOT_DIR, 'creds')
CREDENTIALS_FILE = os.path.join(CREDENTIALS_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(CREDENTIALS_DIR, 'token.pickle')