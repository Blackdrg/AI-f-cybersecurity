with open('D:/AI-F/AI-f/README.md', 'rb') as f:
    raw = f.read()
text = raw.decode('utf-8', errors='replace')
lines = text.split('\n')

# Find the Performance Benchmarks section (which is what we actually need to replace)
for i in range(len(lines)):
    if '### Performance Benchmarks' in lines[i]:
        bench_start = i
        break

# Find the end (next ### section after Performance Benchmarks)
bench_end = None
for i in range(bench_start + 1, len(lines)):
    if lines[i].startswith('### '):
        bench_end = i
        break

print('Benchmark section lines:', bench_start, 'to', bench_end)
print('First line:', lines[bench_start])
if bench_end:
    print('Last line:', lines[bench_end-1])
    print('Next section:', lines[bench_end])
"