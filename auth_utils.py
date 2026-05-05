"""Password hashing via bcrypt (never store plaintext passwords)."""
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    # bcrypt ignores input beyond 72 bytes; truncate so long passwords don't error silently.
    password = password[:72]
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    plain_password = plain_password[:72]
    return pwd_context.verify(plain_password, hashed_password)