import re

# Fix mpc_zkp.py first
with open(r'D:\AI-F\AI-f\backend\app\security\mpc_zkp.py') as f:
    lines = f.readlines()

# Fix lines around 240-340
# protocol_id at line 243 has no indentation, should have 4 spaces
# prove at line 246 has 4 spaces, should have 8
# verify has similar issues

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]

    # Fix class MultiplicationProofProtocol section
    if i == 242:  # def protocol_id - should be indented 4 spaces
        if not line.startswith('    def protocol_id'):
            new_lines.append('    def protocol_id(self) -> str:\n')
        else:
            new_lines.append(line)
        i += 1
    elif i == 243:  # return - should be indented 8 spaces
        if not line.startswith('        return "mul-proof-v1"'):
            new_lines.append('        return "mul-proof-v1"\n')
        else:
            new_lines.append(line)
        i += 1
    elif i == 244:  # blank line
        new_lines.append(line)
        i += 1
    elif i == 245:  # def prove - should be indented 4 spaces
        if line.startswith('    def prove('):
            new_lines.append(line)
        else:
            new_lines.append('    def prove(\n')
        i += 1
    elif i == 246:  # self, - should be 8 spaces
        if line.startswith('        self,'):
            new_lines.append(line)
        else:
            new_lines.append('        self,\n')
        i += 1
    elif i >= 247 and i <= 253:  # params - should be 8 spaces
        if line.startswith('        '):
            new_lines.append(line)
        else:
            new_lines.append('        ' + line.lstrip())
        i += 1
    elif i == 254:  # ) -> Dict
        if line.startswith('    )'):
            new_lines.append(line)
        else:
            new_lines.append('    ) -> Dict[str, Any]:\n')
        i += 1
    elif i >= 255 and i <= 310:  # method body
        if line.startswith('            '):
            new_lines.append(line)
        else:
            new_lines.append('            ' + line.lstrip())
        i += 1
    elif i == 311:  # blank line before verify
        new_lines.append(line)
        i += 1
    elif i == 312:  # def verify
        if line.startswith('    def verify('):
            new_lines.append(line)
        else:
            new_lines.append('    def verify(\n')
        i += 1
    elif i == 313:  # self,
        if line.startswith('        self,'):
            new_lines.append(line)
        else:
            new_lines.append('        self,\n')
        i += 1
    elif i >= 314 and i <= 320:  # params
        if line.startswith('        '):
            new_lines.append(line)
        else:
            new_lines.append('        ' + line.lstrip())
        i += 1
    elif i == 321:  # ) -> bool
        if line.startswith('    )'):
            new_lines.append(line)
        else:
            new_lines.append('    ) -> bool:\n')
        i += 1
    elif i >= 322 and i < len(lines) and i <= 350:  # method body
        if line.startswith('            '):
            new_lines.append(line)
        else:
            new_lines.append('            ' + line.lstrip())
        i += 1
    else:
        new_lines.append(line)
        i += 1

with open(r'D:\AI-F\AI-f\backend\app\security\mpc_zkp.py', 'w') as f:
    f.writelines(new_lines)

print('Fixed mpc_zkp.py')

# Fix mpc_spdz.py
with open(r'D:\AI-F\AI-f\backend\app\security\mpc_spdz.py') as f:
    lines = f.readlines()

# Fix line 755 (0-indexed 754)
if 'aggregated[key] = final_share_val' in lines[754]:
    lines[754] = '            aggregated[key] = final_share_val\n'
    print('Fixed aggregated key assignment indentation')

with open(r'D:\AI-F\AI-f\backend\app\security\mpc_spdz.py', 'w') as f:
    f.writelines(lines)

print('Fixed mpc_spdz.py')
print('Done')