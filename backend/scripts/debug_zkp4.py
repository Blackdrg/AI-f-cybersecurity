import sys, os
sys.path.insert(0, r'D:\AI-F\AI-f\backend')
os.environ['TORCH_CUDA_ARCH_LIST'] = ''

from app.security.mpc_spdz import Share, BeaverTriple, FIELD_PRIME
from app.security.mpc_zkp import ZKPManager, ZKPStatement, MultiplicationProofProtocol

share_a = Share(10, 0)
share_b = Share(5, 0)
share_c = Share(50, 0)
triple = BeaverTriple(a=2, b=3, c=6)

proof = {'protocol': 'mul-proof-v1', 'commitment': 5316911983139663491615228241121378304, 'response': 100720908010022408506264476861779894110, 'claimed_value': 50, 'statement': 'mul_correct', 'timestamp': '2026-05-13T22:19:43.857093', 'party_id': 0}

proto = MultiplicationProofProtocol(FIELD_PRIME)
try:
    result = proto.verify(proof, share_a, share_b, triple, 0, context={'party_id': 0, 'round': 1})
    print("Verify result: {}".format(result))
except Exception as ex:
    print("Verify error: {}".format(ex))
    import traceback
    traceback.print_exc()

# Let's manually trace the verification
print("\nManual verification trace:")
commitment = proof['commitment']
z = proof['response']
claimed = proof['claimed_value']
print("commitment={}, z={}, claimed={}".format(commitment, z, claimed))

ctx = {'share_a': share_a.value % (2**64), 'share_b': share_b.value % (2**64), 'share_c': claimed % (2**64), 'party_id': 0}
print("ctx={}".format(ctx))

import json
ctx_json = json.dumps(ctx, sort_keys=True).encode('utf-8')
domain = proto.protocol_id().encode('utf-8')
data = struct.pack('>Q', commitment % (2**64)) + ctx_json + domain
print("data len={}".format(len(data)))

import hashlib
h = hashlib.sha256()
h.update(data)
digest = h.digest()
challenge = int.from_bytes(digest, 'big') % FIELD_PRIME
print("challenge={}".format(challenge))

lhs = pow(2, z, FIELD_PRIME)
rhs = (commitment * pow(2, claimed * challenge, FIELD_PRIME)) % FIELD_PRIME
print("lhs={}, rhs={}".format(lhs, rhs))
print("Match: {}".format(lhs == rhs))

import struct
# Try the exact verification path
print("\nTrying _hash_challenge:")
try:
    ch2 = proto._hash_challenge(struct.pack('>Q', commitment % (2**64)), ctx)
    print("challenge from _hash_challenge: {}".format(ch2))
except Exception as ex2:
    print("Error: {}".format(ex2))
    import traceback
    traceback.print_exc()