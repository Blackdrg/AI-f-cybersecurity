import os

root = r"D:\AI-F\AI-f\docs"
total_lines = 0
file_count = 0
for dirpath, dirnames, filenames in os.walk(root):
    for f in filenames:
        if f.endswith('.md') or f.endswith('.txt'):
            fp = os.path.join(dirpath, f)
            try:
                with open(fp, 'r', encoding='utf-8', errors='ignore') as fh:
                    lines = len(fh.readlines())
                    total_lines += lines
                    file_count += 1
            except Exception as e:
                pass
print(f"Doc files: {file_count}")
print(f"Total lines: {total_lines}")
