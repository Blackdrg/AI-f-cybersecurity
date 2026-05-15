import sys
import os

# Add the app directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.security import get_password_hash, verify_password

def test_hashing():
    password = "secret-password"
    hashed = get_password_hash(password)
    print(f"Hashed: {hashed}")
    assert hashed.startswith("$argon2id$")
    assert verify_password(password, hashed)
    assert not verify_password("wrong-password", hashed)
    print("Hashing test passed!")

if __name__ == "__main__":
    test_hashing()
