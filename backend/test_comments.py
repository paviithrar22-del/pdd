import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state="sessions/account_1.json")
        page = await context.new_page()
        await page.goto("https://www.instagram.com/testerapp_cyber/")
        await page.wait_for_timeout(3000)
        
        post_links = await page.locator("a[href*='/p/']").all()
        if post_links:
            href = await post_links[0].get_attribute("href")
            if href:
                post_url = f"https://www.instagram.com{href}" if href.startswith("/") else href
                print(f"Going to post: {post_url}")
                await page.goto(post_url)
                await page.wait_for_timeout(4000)
            
            # Dump HTML to debug
            html = await page.content()
            with open("post_debug.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("Saved post_debug.html")

            # Try the JS extraction
            raw = await page.evaluate("""() => {
                const results = [];
                let container = document.querySelector('article') || document.body;
                
                // Get all possible user links (h3 tags or direct links)
                const authorLinks = container.querySelectorAll('h3, a[href^="/"]');
                const seen = new Set();
                
                authorLinks.forEach(link => {
                    const href = link.getAttribute('href');
                    let username = link.innerText ? link.innerText.trim() : '';
                    if (!username && href) username = href.replace(/\\//g, '');
                    
                    if (!username || username.length < 2 || username.length > 30 || username.includes(' ')) return;
                    
                    // Look around for text
                    let parent = link.parentElement;
                    for(let i=0; i<5; i++) {
                        if (!parent) break;
                        const spans = parent.querySelectorAll('span[dir="auto"], div[dir="auto"]');
                        let found = false;
                        for (let el of spans) {
                            const text = el.innerText ? el.innerText.trim() : '';
                            if (text && text !== username && text.length > 1) {
                                if (text.match(/^(Like|Reply|View replies|See translation|Hide replies|Log In|Sign Up)$/i)) continue;
                                if (text.match(/^\\d+[smhdwy]$/)) continue;
                                
                                const key = username + text;
                                if (!seen.has(key)) {
                                    seen.add(key);
                                    results.push({ author: username, content: text });
                                    found = true;
                                    break;
                                }
                            }
                        }
                        if (found) break;
                        parent = parent.parentElement;
                    }
                });
                return results;
            }""")
            print(f"Extracted {len(raw)} comments via JS:")
            for c in raw:
                print(f"  {c['author']}: {c['content']}")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
