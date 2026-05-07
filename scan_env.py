import os
import glob

files = glob.glob('**/*.py', recursive=True)
env_vars = set()

for f in files:
    if os.path.isfile(f):
        try:
            with open(f, 'r', encoding='utf-8', errors='ignore') as file:
                for line in file:
                    if 'os.getenv(' in line:
                        # Extract variable names
                        start = line.find('os.getenv(')
                        if start != -1:
                            content = line[start + 9:]
                            # Find closing parenthesis
                            depth = 1
                            end = 0
                            for i, char in enumerate(content):
                                if char == '(':
                                    depth += 1
                                elif char == ')':
                                    depth -= 1
                                    if depth == 0:
                                        end = i
                                        break
                            if end > 0:
                                var_expr = content[:end]
                                # Extract the first argument (the variable name)
                                var_name = var_expr.split(',')[0].strip()
                                var_name = var_name.strip('"\'').strip()
                                if var_name and var_name.isupper():
                                    env_vars.add(var_name)
        except Exception as e:
            pass

for var in sorted(env_vars):
    print(var)
