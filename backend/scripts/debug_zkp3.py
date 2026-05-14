import sys, os
sys.path.insert(0, r'D:\AI-F\AI-f\backend')
os.environ['TORCH_CUDA_ARCH_LIST'] = ''

from app.security.mpc_spdz import Share, BeaverTriple, FIELD_PRIME
from app.security.mpc_zkp import ZKPManager, ZKPStatement

share_a = Share(10, 0)
share_b = Share(5, 0)
share_c = Share(50, 0)
triple = BeaverTriple(a=2, b=3, c=6)

# Check expected
d = (10 - 2) % FIELD_PRIME
e = (5 - 3) % FIELD_PRIME
expected = (6 + d*3 + e*2 + d*e) % FIELD_PRIME
print("d={}, e={}, expected={}, share_c={}".format(d, e, expected, share_c.value))
print("Match: {}".format(expected == share_c.value))

manager = ZKPManager(FIELD_PRIME)
try:
    proof = manager.generate_proof(
        ZKPStatement.MULTIPLICATION_CORRECT,
        witness={'share_a': share_a, 'share_b': share_b, 'share_c': share_c, 'triple': triple, 'party_id': 0},
        public_inputs={'share_a': share_a, 'share_b': share_b, 'triple': triple, 'party_id': 0},
        context={'party_id': 0, 'round': 1}
    )
    print("Proof: {}".format(proof))
    verified = manager.verify_proof(
        ZKPStatement.MULTIPLICATION_CORRECT,
        proof,
        public_inputs={'share_a': share_a, 'share_b': share_b, 'triple': triple, 'party_id': 0},
        context={'party_id': 0, 'round': 1}
    )
    print("Verified: {}".format(verified))
except Exception as ex:
    print("Error: {}".format(ex))
    import traceback
    traceback.print_exc()

sys.stdout.flush()