with open('app/security/mpc_spdz.py') as f:
    lines = f.readlines()

# Find and replace compute_private_sum method body (lines 689-714)
new_lines = []
i = 0
while i < len(lines):
    if i == 688:  # line 689 (0-indexed 688)
        # Skip old method body until line 715
        # Replace with new implementation
        new_lines.append('        self._round_counter += 1\n')
        new_lines.append('        round_id = f"sum_r{self._round_counter}"\n')
        new_lines.append('\n')
        new_lines.append('        n = self.n\n')
        new_lines.append('        field = self.parties[0].field\n')
        new_lines.append('\n')
        new_lines.append('        total_sum = 0\n')
        new_lines.append('        for party_idx, party_input in enumerate(party_inputs):\n')
        new_lines.append('            party = self.parties[party_idx]\n')
        new_lines.append('            for var_id, value in party_input.items():\n')
        new_lines.append('                # Secret-share value among all parties using additive sharing\n')
        new_lines.append('                shares = party.share_secret(value, f"{round_id}_{var_id}")\n')
        new_lines.append('                # Sum all shares (reconstruct by summing all party shares)\n')
        new_lines.append('                for s in shares:\n')
        new_lines.append('                    total_sum = field.add(total_sum, s.value)\n')
        new_lines.append('\n')
        new_lines.append('        return {\n')
        new_lines.append('            "session_id": self.session_id,\n')
        new_lines.append('            "round": round_id,\n')
        new_lines.append('            "result": total_sum,\n')
        new_lines.append('            "n_parties": n,\n')
        new_lines.append('            "timestamp": datetime.utcnow().isoformat()\n')
        new_lines.append('        }\n')
        # Skip old body
        while i < len(lines) and not lines[i].strip().startswith('async def compute_secure_aggregation'):
            i += 1
    else:
        new_lines.append(lines[i])
        i += 1

with open('app/security/mpc_spdz.py', 'w') as f:
    f.writelines(new_lines)
print('Done')