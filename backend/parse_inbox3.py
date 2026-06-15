import re
from collections import Counter
import json

html = open('inbox_debug.html', encoding='utf-8').read()

# Try to find things under "Thread list"
idx = html.find('Thread list')
if idx != -1:
    print("Found 'Thread list' aria-label.")
    start = max(0, idx - 500)
    end = min(len(html), idx + 2000)
    # print(html[start:end])

# Look for typical Instagram thread markers in text, e.g. "new messages"
matches = [m.start() for m in re.finditer(r'new messages?', html, re.IGNORECASE)]
print(f"Found {len(matches)} matches for 'new message'")
for m in matches:
    start = max(0, m - 300)
    end = min(len(html), m + 300)
    print("----")
    print(html[start:end])
