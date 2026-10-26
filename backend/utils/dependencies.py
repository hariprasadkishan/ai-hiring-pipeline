from fastapi import Depends
from database import get_db
from utils.security import oauth2_scheme, verify_token_str

def get_current_user_data(token: str = Depends(oauth2_scheme)) -> dict:
    return verify_token_str(token)
