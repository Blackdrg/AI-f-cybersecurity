import re

with open('app/security/mpc_spdz.py') as f:
    content = f.read()

# Fix compute_private_sum - replace the entire method body
old = '''async def compute_private_sum(
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

        # Each party locally sums their shares of all inputs
        local_sums = []
        for party_idx, party_input in enumerate(party_inputs):
            party = self.parties[party_idx]
            total = 0
            for var_id, value in party_input.items():
                # Share this value among all parties
                shares = party.share_secret(value, f"{round_id}_{var_id}")
                # Sum shares locally (for additive sharing)
                total = party.field.add(total, shares[party.party_id].value)
            local_sums.append(total)

        # Now reconstruct sum by exchanging shares (simplified)
        # Real protocol: parties send shares to aggregator or all-to-all
        total_sum = sum(local_sums) % self.parties[0].field.prime

        return {
            "session_id": self.session_id,
            "round": round_id,
            "result": total_sum,
            "n_parties": self.n,
            "timestamp": datetime.utcnow().isoformat()
        }'''

new = '''async def compute_private_sum(
        self,
        party_inputs: List[Dict[int, int]]
    ) -> Dict[str, Any]:
        """
        Compute sum of private inputs from all parties.

        Each party i holds input x_i^j for party j.
        Goal: sum_{i,j} x_i^j  (all inputs summed)

        Protocol:
          Each party secret-shares each input value among all parties
          Then parties reconstruct the sum of all shares
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

if old in content:
    content = content.replace(old, new)
    print('Replaced compute_private_sum')
else:
    print('WARNING: compute_private_sum old text not found')

with open('app/security/mpc_spdz.py', 'w') as f:
    f.write(content)
print('Done')