base = r'D:\AI-F\AI-f\backend'
with open(base + r'\app\security\mpc_spdz.py') as f:
    lines = f.readlines()

# Fix compute_secure_aggregation - sum all shares, not just party 0
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # Look for the specific pattern in compute_secure_aggregation
    if 'final_share_val = 0' in line and i > 740:
        # Found the aggregation section, replace the loop
        new_lines.append(line)  # Keep "final_share_val = 0"
        i += 1
        # Skip old loop body until we find the aggregated assignment
        while i < len(lines) and 'aggregated[key]' not in lines[i]:
            i += 1
        # Insert new proper aggregation
        new_lines.append('             for shares in shares_per_party:\n')
        new_lines.append('                 # Sum ALL shares (additive secret sharing: sum of all shares = secret)\n')
        new_lines.append('                 for s in shares:\n')
        new_lines.append('                     final_share_val = self.parties[0].field.add(\n')
        new_lines.append('                         final_share_val, s.value\n')
        new_lines.append('                     )\n')
        new_lines.append('\n')
        new_lines.append('             aggregated[key] = final_share_val\n')
        # Now skip until we find the next part after aggregated[key] = final_share_val
        while i < len(lines) and 'aggregated[key]' not in lines[i]:
            i += 1
        i += 1  # Skip the aggregated[key] line we just wrote
    else:
        new_lines.append(line)
        i += 1

with open(base + r'\app\security\mpc_spdz.py', 'w') as f:
    f.writelines(new_lines)
print('Done')