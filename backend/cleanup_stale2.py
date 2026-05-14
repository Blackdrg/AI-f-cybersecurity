import shutil, os
sp = r"D:\AI-F\AI-f\.venv\Lib\site-packages"
cleaned = 0
for d in os.listdir(sp):
    if d.startswith('~'):
        full = os.path.join(sp, d)
        if os.path.isdir(full):
            shutil.rmtree(full, ignore_errors=True)
            print(f"Removed dir: {d}")
            cleaned += 1
        elif os.path.isfile(full):
            try:
                os.remove(full)
                print(f"Removed file: {d}")
                cleaned += 1
            except:
                pass
print(f"\nCleaned {cleaned} stale entries")