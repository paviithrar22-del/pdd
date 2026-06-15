import asyncio
import sys
from playwright.async_api import async_playwright

async def test():
    try:
        async with async_playwright() as p:
            print("Launching browser...")
            browser = await p.chromium.launch()
            print('Launch OK')
            await browser.close()
    except Exception as e:
        print(f"Error in test: {e}")

def run():
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test())

if __name__ == '__main__':
    import threading
    t = threading.Thread(target=run)
    t.start()
    t.join()
