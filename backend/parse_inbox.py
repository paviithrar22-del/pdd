import re

html = open('inbox_debug.html', encoding='utf-8').read()

# Find all href values containing direct
hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)
direct_links = [h for h in hrefs if 'direct' in h.lower()]
print(f"Direct-related hrefs ({len(direct_links)}):")
for h in direct_links[:30]:
    print(f"  {h}")

# Check what sections exist
has_requests = 'request' in html.lower()
print(f"\nPage mentions 'request': {has_requests}")

# Find all anchor links
all_links = set(hrefs)
print(f"\nAll unique hrefs ({len(all_links)}):")
for h in sorted(all_links)[:30]:
    print(f"  {h}")
