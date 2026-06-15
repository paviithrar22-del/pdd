import re
html = open('inbox_debug.html', encoding='utf-8').read()
links = re.findall(r'<a[^>]+href=[\'"]([^\'"]+)[\'"]', html)
print(f'Found {len(links)} links')
for l in links:
    if '/direct/' in l:
        print(l)
