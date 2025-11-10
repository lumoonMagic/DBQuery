import time, bcrypt, json
from pathlib import Path

def hash_password(pwd: str) -> str:
    return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()

def verify_password(pwd: str, hashed: str) -> bool:
    return bcrypt.checkpw(pwd.encode(), hashed.encode())

def timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")

def load_json(path):
    return json.loads(Path(path).read_text())
