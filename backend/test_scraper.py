import asyncio
import sys
import logging
import os
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_test():
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            logger.info("Navigating to Instagram...")
            await page.goto("https://www.instagram.com/", timeout=30000)
            await page.wait_for_timeout(5000)
            
            await page.screenshot(path="instagram_homepage.png")
            logger.info("Saved instagram_homepage.png")
            
            login_inputs = await page.locator("input[name='username']").count()
            logger.info(f"Login inputs count: {login_inputs}, URL: {page.url}")
            
            # Print page content
            content = await page.content()
            logger.info(f"Page content length: {len(content)}")

            await browser.close()
    except Exception as e:
        logger.error(f"Error: {e}")

def run():
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_test())

if __name__ == '__main__':
    run()
