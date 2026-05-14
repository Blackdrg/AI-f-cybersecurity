import sys, os
sys.path.insert(0, r'D:\AI-F\AI-f\backend')
os.chdir(r'D:\AI-F\AI-f\backend')

from datetime import datetime
from app.security.pqc import PQCKeyStore, PQCKeyMetadata, PQCAlgorithm
import tempfile

with tempfile.TemporaryDirectory() as tmp:
    keystore = PQCKeyStore(keys_dir=tmp)

    key_data = b"test_secret_key_material"
    meta = PQCKeyMetadata(
        algorithm="kyber768",
        version=1,
        created_at=datetime.utcnow().isoformat(),
        key_type="kem"
    )

    try:
        stored = keystore.store_key("test-key", key_data, meta)
        print("store_key result: {}".format(stored))
    except Exception as e:
        print("store_key error: {}".format(e))
        import traceback
        traceback.print_exc()

    try:
        loaded = keystore.load_key("test-key")
        print("load_key result: {}".format(loaded))
    except Exception as e:
        print("load_key error: {}".format(e))
        import traceback
        traceback.print_exc()

    # List files
    print("Files in keys_dir: {}".format(os.listdir(tmp)))