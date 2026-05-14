import sys
sys.path.insert(0, r'D:\AI-F\AI-f\backend')

from app.security.mpc_spdz import Share, BeaverTriple, FIELD_PRIME
from app.security.mpc_zkp import ZKPManager, ZKPStatement

# Create test data
share_a = Share(10, 0)
share_b = Share(5, 0)
share_c = Share(50, 0)  # c = a*b = 10*5 = 50
triple = BeaverTriple(a=2, b=3, c=6)

# Check the expected calculation
field_prime = FIELD_PRIME
d = (10 - 2) % field_prime
e = (5 - 3) % field_prime
expected = (6 + d*3 + e*2 + d*e) % field_prime
print(f"d={d}, e={e}, expected={expected}, share_c={share_c.value}")
print(f"Match: {expected == share_c.value}")

# Try proof generation
manager = ZKPManager(FIELD_PRIME)
try:
    proof = manager.generate_proof(
        ZKPStatement.MULTIPLICATION_CORRECT,
        witness={
            'share_a': share_a,
            'share_b': share_b,
            'share_c': share_c,
            'triple': triple,
            'party_id': 0
        },
        public_inputs={
            'share_a': share_a,
            'share_b': share_b,
            'triple': triple,
            'party_id': 0
        },
        context={'party_id': 0, 'round': 1}
    )
    print(f"Proof generated: {proof}")

    verified = manager.verify_proof(
        ZKPStatement.MULTIPLICATION_CORRECT,
        proof,
        public_inputs={
            'share_a': share_a,
            'share_b': share_b,
            'triple': triple,
            'party_id': 0
        },
        context={'party_id': 0, 'round': 1}
    )
    print(f"Verified: {verified}")
except Exception as ex:
    print(f"Error: {ex}")
    import traceback
    traceback.print_exc()