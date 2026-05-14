import re

base = r'D:\AI-F\AI-f\backend'

# ===============================
# Fix 1: compute_private_sum (sum raw values, not shares)
# ===============================
with open(base + r'\app\security\mpc_spdz.py') as f:
    content = f.read()

old = '''        self._round_counter += 1
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

new = '''        self._round_counter += 1
        round_id = f"sum_r{self._round_counter}"

        field = self.parties[0].field

        # Sum all input values across all parties
        total_sum = 0
        for party_input in party_inputs:
            for value in party_input.values():
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
    # Debug: print lines around the method
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'async def compute_private_sum' in line:
            for j in range(max(0,i-2), min(len(lines), i+30)):
                print(f"{j}: {lines[j]}")
            break

with open(base + r'\app\security\mpc_spdz.py', 'w') as f:
    f.write(content)