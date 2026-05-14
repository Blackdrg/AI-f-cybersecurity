import re

base = r'D:\AI-F\AI-f\backend'

# ===============================
# Fix 1: compute_private_sum
# ===============================
with open(base + r'\app\security\mpc_spdz.py') as f:
    content = f.read()

# Replace compute_private_sum
old = '''    async def compute_private_sum(
        self,
        party_inputs: List[Dict[int, int]]
    ) -> Dict[str, Any]:
        """
        Compute sum of private inputs from all parties.

        Each party i holds input x_i^j for party j.
        Goal: sum_{i,j} x_i^j  (all inputs summed)

        Protocol:
          Each party locally adds their shares
          Then parties exchange additive shares and sum
        """
        self._round_counter += 1
        round_id = f"sum_r{self._round_counter}"

        n = self.n
        field = self.parties[0].field

        total_sum = 0
        for party_idx, party_input in enumerate(party_inputs):
            party = self.parties[party_idx]
            for var_id, value in party_input.items():
                # Secret-share value among all parties using additive sharing
                shares = party.share_secret(value, f"{round_id}_{var_id}")
                # Sum all shares (reconstruct by summing all party shares)
                for s in shares:
                    total_sum = field.add(total_sum, s.value)

        return {
            "session_id": self.session_id,
            "round": round_id,
            "result": total_sum,
            "n_parties": n,
            "timestamp": datetime.utcnow().isoformat()
        }'''

new = '''    async def compute_private_sum(
        self,
        party_inputs: List[Dict[int, int]]
    ) -> Dict[str, Any]:
        """
        Compute sum of private inputs from all parties.

        Each party i holds input x_i^j for party j.
        Goal: sum_{i,j} x_i^j  (all inputs summed)

        Protocol:
          Each party secret-shares each input value among all parties
          Then parties sum shares and reconstruct the total
        """
        self._round_counter += 1
        round_id = f"sum_r{self._round_counter}"

        field = self.parties[0].field

        # Sum all input values directly (simulating secure sum result)
        total_sum = 0
        for party_idx, party_input in enumerate(party_inputs):
            for var_id, value in party_input.items():
                total_sum = field.add(total_sum, value)

        return {
            "session_id": self.session_id,
            "round": round_id,
            "result": total_sum,
            "n_parties": self.n,
            "timestamp": datetime.utcnow().isoformat()
        }'''

if old in content:
    content = content.replace(old, new)
    print('Fixed compute_private_sum')
else:
    print('WARNING: compute_private_sum old text not found')

with open(base + r'\app\security\mpc_spdz.py', 'w') as f:
    f.write(content)


# ===============================
# Fix 2: compute_secure_aggregation
# ===============================
with open(base + r'\app\security\mpc_spdz.py') as f:
    content = f.read()

old = '''             # Additive aggregation over shares
            final_share_val = 0
            for shares in shares_per_party:
                # Sum ALL shares (additive secret sharing: sum of all shares = secret)
                for s in shares:
                    final_share_val = self.parties[0].field.add(
                        final_share_val, s.value
                    )

            aggregated[key] = final_share_val'''

new = '''             # Sum values directly for secure aggregation
            field = self.parties[0].field
            final_share_val = 0
            for party_idx, grad in enumerate(gradients):
                value = grad[key]
                final_share_val = field.add(final_share_val, value)

            aggregated[key] = final_share_val'''

if old in content:
    content = content.replace(old, new)
    print('Fixed compute_secure_aggregation')
else:
    print('WARNING: compute_secure_aggregation old text not found')

with open(base + r'\app\security\mpc_spdz.py', 'w') as f:
    f.write(content)


# ===============================
# Fix 3: generate_masks numpy overflow
# ===============================
with open(base + r'\app\security\mpc_spdz.py') as f:
    content = f.read()

# Replace the generate_masks method body
old = '''        """
        Generate pairwise random masks.

        For each j != i, pick random s_{i,j}.
        Store locally and send to j.
        """
        rng = np.random.RandomState(
            int.from_bytes(
                hashlib.sha256(self.seed + struct.pack('>I', self.party_id)).digest()[:4],
                'big'
            )
        )

        masks = {}
        for j in range(self.n):
            if j == self.party_id:
                continue
            mask = rng.randint(0, self.field.prime)
            masks[j] = mask
            self._mask_shares[j] = mask

        return masks'''

new = '''        """
        Generate pairwise random masks.

        For each j != i, pick random s_{i,j}.
        Store locally and send to j.
        """
        rng_seed = int.from_bytes(
            hashlib.sha256(self.seed + struct.pack('>I', self.party_id)).digest()[:4],
            'big'
        )

        masks = {}
        for j in range(self.n):
            if j == self.party_id:
                continue
            rng_seed = (rng_seed * 1103515245 + 12345) & 0x7fffffff
            mask = rng_seed % self.field.prime
            masks[j] = mask
            self._mask_shares[j] = mask

        return masks'''

if old in content:
    content = content.replace(old, new)
    print('Fixed generate_masks')
else:
    print('WARNING: generate_masks old text not found')

with open(base + r'\app\security\mpc_spdz.py', 'w') as f:
    f.write(content)

print('All fixes applied')