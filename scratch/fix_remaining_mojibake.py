with open('D:\\AI-F\\AI-f\\README.md', 'rb') as f:
    content = f.read()

# Fix remaining â€¢ -> • (bullet)
content = content.replace(b'\xe2\x80\x9e\xe2\x84\xa2', b'\xe2\x80\xa2')
# Fix remaining âš–ï¸ -> ⚖️
content = content.replace(b'\xc3\xa2\xe2\x80\x93\xc3\xaf\xc2\xb8\xc3\xa8\xe2\x9d\x8e', b'\xe2\x9a\x96\xef\xb8\x8f')
# Fix âš›ï¸ -> ⚛️
content = content.replace(b'\xc3\xa2\xe2\x80\xba\xc3\xaf\xc2\xb8\xc3\xa8\xef\xb8\x8f', b'\xe2\x9a\x9b')

with open('D:\\AI-F\\AI-f\\README.md', 'wb') as f:
    f.write(content)
print('Done fixing remaining mojibake')