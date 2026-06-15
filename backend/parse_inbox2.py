import re

html = open('inbox_debug.html', encoding='utf-8').read()

# Look for 'new message' in the HTML text and get a window around it
matches = [m.start() for m in re.finditer(re.escape('new message'), html, re.IGNORECASE)]
print(f"Found {len(matches)} occurrences of 'new message'")

for m in matches:
    start = max(0, m - 300)
    end = min(len(html), m + 300)
    print("-----")
    print(html[start:end])

# Also check for roles like listitem
listitems = re.findall(r'<div[^>]*role=["\']listitem["\'][^>]*>(.*?)</div>', html, re.DOTALL)
print(f"\nFound {len(listitems)} listitems")
if listitems:
    print(listitems[0][:300])
