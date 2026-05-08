
import sys

file_path = r'd:\AI-F\AI-f\README.md'

with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# Line numbers are 1-indexed, so we subtract 1
lines[381] = "## 🏗️ Architecture Overview\n" # Index 381 is line 382
lines[8795] = "## 🏗️ Architecture Overview\n" # Index 8795 is line 8796

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Architecture headers fixed by line number.")
