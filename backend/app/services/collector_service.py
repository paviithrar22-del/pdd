"""
Instagram Collector Service
Uses Playwright to scrape comments and DMs.
Session expires after 15 minutes.
"""
import asyncio
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import cast
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import decrypt
from app.database.base import SessionLocal
from app.models.instagram import InstagramAccount, Post
from app.models.content import Comment, Message, Conversation
from app.models.user import User
from app.services.analysis_pipeline import analyze_content

logger = logging.getLogger(__name__)

_active_monitors: dict[int, threading.Event] = {}


def is_session_expired(account: InstagramAccount) -> bool:
    if not account.session_started_at:
        return True
    expiry = account.session_started_at + timedelta(minutes=settings.INSTAGRAM_SESSION_EXPIRE_MINUTES)
    return datetime.now(timezone.utc).replace(tzinfo=None) > expiry


async def _scrape_comments(page, post_url: str) -> list[dict]:
    """
    Scrape comments from an Instagram post page.
    Uses exact stable selectors confirmed from real Instagram HTML:
    - Username: span._ap3a._aaco (stable Instagram class)
    - Comment text: div[class*="x1cy8zhl"] > span[dir="auto"] (comment wrapper)
    """
    comments = []
    try:
        for retry in range(2):
            try:
                await page.goto(post_url, timeout=40000)
                break
            except Exception as goto_err:
                logger.warning(f"_scrape_comments goto retry {retry}: {goto_err}")
                await page.wait_for_timeout(2000)

        await page.wait_for_timeout(5000)

        # Dismiss notification/save-info popups only (safe version)
        await _dismiss_modals_safe(page)
        await page.wait_for_timeout(2000)

        # Wait for post content to load
        loaded = False
        for selector in ["article", "ul[class]", "span._ap3a"]:
            try:
                await page.wait_for_selector(selector, timeout=8000)
                loaded = True
                logger.info(f"[Comments] Page loaded with '{selector}' for {post_url}")
                break
            except Exception:
                continue

        if not loaded:
            logger.warning(f"[Comments] Could not confirm page load for {post_url}")

        # Click 'Load more comments' up to 5 times
        for _ in range(5):
            try:
                load_more = page.locator(
                    "button:has-text('Load more comments'), "
                    "span:has-text('Load more comments'), "
                    "svg[aria-label='Load more comments']"
                ).first
                if await load_more.is_visible(timeout=1500):
                    await load_more.click()
                    await page.wait_for_timeout(1500)
                else:
                    break
            except Exception:
                break

        # PRIMARY: Use exact stable selectors from real Instagram HTML
        raw = await page.evaluate("""() => {
            const results = [];
            const SKIP = /^(Like|Reply|View replies|See translation|Hide replies|Report|Hidden by Instagram|Follow|Suggested for you)$/i;
            const TIMESTAMP = /^\\d+[smhdwy]$/;

            // PRIMARY: div[class*="x1cy8zhl"] contains comment text (confirmed from real HTML)
            const commentDivs = document.querySelectorAll('div[class*="x1cy8zhl"]');
            commentDivs.forEach(div => {
                const textSpan = div.querySelector('span[dir="auto"]');
                if (!textSpan) return;
                const text = (textSpan.innerText || '').trim();
                if (!text || text.length < 1 || SKIP.test(text) || TIMESTAMP.test(text)) return;

                // Find username by traversing UP to span._ap3a._aaco
                let container = div.parentElement;
                let author = null;
                for (let i = 0; i < 15; i++) {
                    if (!container) break;
                    const userSpan = container.querySelector('span._ap3a._aaco');
                    if (userSpan) {
                        author = (userSpan.innerText || '').trim();
                        break;
                    }
                    container = container.parentElement;
                }

                if (author && text && author !== text) {
                    results.push({ author, content: text });
                }
            });

            // FALLBACK: Use _ap3a spans and find sibling comment text
            if (results.length === 0) {
                document.querySelectorAll('span._ap3a._aaco').forEach(userEl => {
                    const author = (userEl.innerText || '').trim();
                    if (!author || author.length > 30) return;

                    let container = userEl.parentElement;
                    let commentText = null;
                    for (let depth = 0; depth < 12; depth++) {
                        if (!container) break;
                        for (const span of container.querySelectorAll('span[dir="auto"]')) {
                            if (span.closest('a')) continue;
                            if (span.contains(userEl)) continue;
                            const text = (span.innerText || '').trim();
                            if (!text || text === author || SKIP.test(text) || TIMESTAMP.test(text)) continue;
                            commentText = text;
                            break;
                        }
                        if (commentText) break;
                        container = container.parentElement;
                    }

                    if (author && commentText) {
                        results.push({ author, content: commentText });
                    }
                });
            }

            // Deduplicate by content
            const seen = new Set();
            return results.filter(r => {
                if (seen.has(r.content)) return false;
                seen.add(r.content);
                return true;
            });
        }""")

        if raw and len(raw) > 0:
            logger.info(f"[Comments] JS found {len(raw)} comments for {post_url}")
            for item in raw:
                if item.get("author") and item.get("content"):
                    comments.append({"author": item["author"], "content": item["content"]})
        else:
            logger.warning(f"[Comments] JS returned 0 results for {post_url}")

        logger.info(f"[Comments] Final: {len(comments)} comments from {post_url}")

    except Exception as e:
        logger.error(f"Comment scrape error for {post_url}: {e}", exc_info=True)
    return comments


async def _dismiss_modals_safe(page):
    """Dismiss ONLY notification/save-info popups. Does NOT remove post content dialogs."""
    try:
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)
        for label in ["Not Now", "Cancel", "Close"]:
            try:
                btns = await page.locator(f"text='{label}'").all()
                for btn in btns:
                    if await btn.is_visible(timeout=400):
                        await btn.click(force=True)
                        await page.wait_for_timeout(700)
            except Exception:
                pass
    except Exception:
        pass


async def _dismiss_modals(page):
    """Aggressively dismiss any modals overlaying the page."""
    try:

        # Press Escape a couple of times
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)
        # Try clicking common dismiss buttons like "Not Now" or "Cancel"
        try:
            not_now_btns = await page.locator("text='Not Now'").all()
            for btn in not_now_btns:
                if await btn.is_visible(timeout=500):
                    await btn.click(force=True)
                    await page.wait_for_timeout(1000)
        except Exception:
            pass

        try:
            cancel_btns = await page.locator("text='Cancel'").all()
            for btn in cancel_btns:
                if await btn.is_visible(timeout=500):
                    await btn.click(force=True)
                    await page.wait_for_timeout(1000)
        except Exception:
            pass
        # Use JavaScript to remove overlay divs that intercept pointer events
        await page.evaluate('''
            const overlays = document.querySelectorAll('div[role="dialog"]');
            overlays.forEach(el => el.remove());
            // Also remove any fixed-position pointer-intercepting divs
            document.querySelectorAll('div').forEach(el => {
                const style = window.getComputedStyle(el);
                if (style.position === 'fixed' && el.children.length === 0 && style.zIndex > 10) {
                    el.remove();
                }
            });
        ''')
    except Exception as e:
        logger.debug(f"Modal dismiss attempt: {e}")


async def _scrape_dms(page, username=None, password=None) -> list[dict]:
    """
    Scrape DM threads by navigating DIRECTLY to thread URLs — no clicking required.
    This bypasses any overlay modals that intercept pointer events.
    """
    messages = []
    try:        # We just need the main inbox
        inbox_url = "https://www.instagram.com/direct/inbox/"
        logger.info(f"Navigating to {inbox_url} ...")
        await page.goto(inbox_url, timeout=30000)
        await page.wait_for_timeout(3000)

        # --- Dismiss ALL popups before doing anything else ---
        for attempt in range(5):
            dismissed = False
            
            # "Turn on Notifications" or "Save Info" popup — click "Not Now"
            not_now = page.locator("text='Not Now'")
            try:
                if await not_now.count() > 0:
                    for i in range(await not_now.count()):
                        if await not_now.nth(i).is_visible():
                            logger.info(f"Dismissing 'Not Now' popup (attempt {attempt+1})...")
                            await not_now.nth(i).click(force=True)
                            await page.wait_for_timeout(1500)
                            dismissed = True
            except Exception:
                pass
            
            # "Save your login info?" popup
            save_info = page.locator("button:has-text('Save Info'), button:has-text('Not Now')")
            if await save_info.count() > 0 and await save_info.last.is_visible():
                logger.info("Dismissing 'Save login info' popup...")
                await save_info.last.click(force=True)
                await page.wait_for_timeout(1000)
                dismissed = True

            # Generic dialog close via SVG or button
            dialog = page.locator("div[role='dialog']")
            if await dialog.count() > 0 and await dialog.first.is_visible():
                logger.info("Removing dialog via JavaScript...")
                await page.evaluate('''
                    document.querySelectorAll('div[role="dialog"]').forEach(el => el.remove());
                ''')
                await page.wait_for_timeout(500)
                dismissed = True
            
            if not dismissed:
                break  # No more popups found

        # --- Wait for threads to load in the sidebar ---
        logger.info("Waiting for DM threads to load in sidebar...")
        try:
            # Wait for either 'listitem' or the 'Thread list' container
            await page.wait_for_selector("div[role='listitem'], div[aria-label='Thread list']", timeout=10000)
        except Exception:
            logger.warning("Timeout waiting for thread list container.")

        # Try to find clickable thread elements in the sidebar
        all_listitems = await page.locator("div[role='listitem']").all()
        if len(all_listitems) == 0:
            # Fallback to looking inside the 'Thread list' container for clickable items
            all_listitems = await page.locator("div[aria-label='Thread list'] div[role='button']").all()

        valid_threads = []
        for item in all_listitems:
            try:
                txt = await item.inner_text(timeout=1000)
                if "Your note" not in txt and "Requests" not in txt:
                    valid_threads.append(item)
            except Exception:
                pass

        logger.info(f"Found {len(valid_threads)} valid threads in the sidebar.")

        if len(valid_threads) == 0:
            logger.warning("No threads found. Saving inbox_debug.html.")
            html = await page.content()
            with open("inbox_debug.html", "w", encoding="utf-8") as f:
                f.write(html)
            return messages

        # --- Step 2: Click each thread and extract messages ---
        # We limit to the top 5 recent threads
        for i in range(min(5, len(valid_threads))):
            participant = f"thread_{i+1}"
            try:
                thread_element = valid_threads[i]
                logger.info(f"Clicking thread #{i+1}...")
                
                # force=True bypasses any invisible overlays intercepting pointer events!
                # Try to click the inner text element, as the outer listitem might not have the onClick
                inner_text = thread_element.locator("div[dir='auto']").first
                if await inner_text.count() > 0:
                    await inner_text.click(force=True)
                else:
                    await thread_element.click(force=True)
                    
                await page.wait_for_timeout(3000)
                
                # Check if URL changed to a thread URL
                current_url = page.url
                if "/direct/t/" not in current_url:
                    logger.warning(f"Click on thread #{i+1} did not navigate to a thread. Current URL: {current_url}")
                    continue
                
                participant_id = current_url.split('/direct/t/')[-1].strip('/')
                
                # Reliable JS extraction from the main chat header
                participant = participant_id
                participant_js = await page.evaluate('''() => {
                    const chatHeader = document.querySelector('div[role="main"] header');
                    if (chatHeader) {
                        const profileLink = chatHeader.querySelector('a[href^="/"]');
                        if (profileLink) {
                            const href = profileLink.getAttribute('href');
                            if (href && href.length > 2 && !href.includes('/direct/')) {
                                return href.replace(/\\//g, '');
                            }
                        }
                        const spans = chatHeader.querySelectorAll('span[dir="auto"]');
                        for (let span of spans) {
                            const text = span.innerText;
                            if (text && text.length > 0 && text.length < 30 && !text.includes('Active') && !text.includes('seen')) {
                                return text;
                            }
                        }
                    }
                    return null;
                }''')
                
                if participant_js and len(participant_js) < 30:
                    participant = participant_js
                        
                logger.info(f"Opened thread with {participant} -> {current_url}")
                
                # Wait extra for chat to fully load
                await page.wait_for_timeout(2000)
                
                # Dismiss any popups that appeared in the thread
                await _dismiss_modals(page)
                
                # Extract messages using JS, scoped to the main chat column
                extracted_msgs = await page.evaluate('''() => {
                    const messages = [];
                    const seen = new Set();
                    
                    // Find the message input box to locate chat container
                    const inputArea = document.querySelector('div[aria-label="Message"]') 
                                    || document.querySelector('div[contenteditable="true"]')
                                    || document.querySelector('textarea');
                    
                    let chatContainer = null;
                    if (inputArea) {
                        // Walk up until we find a wide container (the main chat column)
                        let curr = inputArea;
                        for(let i = 0; i < 12; i++) {
                            if(curr.parentElement) {
                                curr = curr.parentElement;
                                // Stop when we reach the top-level column div
                                if(curr.offsetWidth > 300 && curr.offsetHeight > 400) {
                                    chatContainer = curr;
                                    break;
                                }
                            }
                        }
                    }
                    
                    if (!chatContainer) {
                        chatContainer = document.body;
                    }
                    
                    // Collect all message text blocks, but ONLY ones with dir=auto
                    // and skip any that are pure-emoji or timestamps
                    const textElements = chatContainer.querySelectorAll(
                        'div[dir="auto"]:not(div[aria-label="Message"] *), span[dir="auto"]'
                    );
                    textElements.forEach(el => {
                        // Skip elements that contain child elements with dir=auto (avoid duplicates)
                        const hasChildDirAuto = el.querySelector('[dir="auto"]');
                        if (hasChildDirAuto) return;
                        
                        const text = el.innerText ? el.innerText.trim() : "";
                        if (!text || text.length < 3) return;
                        if (seen.has(text)) return;
                        seen.add(text);
                        messages.push(text);
                    });
                    return messages;
                }''')
                
                logger.info(f"Found {len(extracted_msgs)} unique text elements in thread #{i+1} ({participant})")
                
                if len(extracted_msgs) == 0:
                    html = await page.content()
                    safe_name = participant.replace("/", "_").replace("\\", "_")
                    with open(f"thread_{safe_name}_debug.html", "w", encoding="utf-8") as f:
                        f.write(html)
                        
                import re as _re
                # UI noise: sidebar labels, timestamps (1m, 2h, 3d), UI actions
                SKIP_EXACT = {
                    "Home", "Search", "Explore", "Reels", "Messages", "Notifications",
                    "Create", "Profile", "More", "Also from Meta", "New note",
                    "Your note", "Shared with followers you follow back",
                    "Send a message", "Open Camera", "Voice clip",
                }
                SKIP_CONTAINS = [
                    "Sent an attachment", "Shared a reel", "Liked a message",
                    "Reacted to", "Active now", "new messages", "You replied",
                    "Shared a post", "Shared a story",
                ]
                # Pattern: pure timestamps like "1m", "2h", "5d", "Just now"
                TIMESTAMP_PATTERN = _re.compile(r'^(\d+[smhdw]|just now|yesterday|\d{1,2}:\d{2}(?: [ap]m)?)$', _re.IGNORECASE)
                
                seen_msgs_in_thread = set()
                for text in extracted_msgs[-50:]:
                    try:
                        clean_text = " ".join(text.split('\n')).strip()
                        
                        # Minimum length — real messages are at least 4 chars
                        if not clean_text or len(clean_text) < 4:
                            continue
                        # Exact UI label skip
                        if clean_text in SKIP_EXACT:
                            continue
                        # Timestamp pattern skip
                        if TIMESTAMP_PATTERN.match(clean_text):
                            continue
                        # Contains skip
                        if any(p.lower() in clean_text.lower() for p in SKIP_CONTAINS):
                            continue
                        # Pure numeric strings (like counts)
                        if clean_text.replace(",", "").replace(".", "").isdigit():
                            continue
                        # Deduplicate within thread
                        if clean_text in seen_msgs_in_thread:
                            continue
                        seen_msgs_in_thread.add(clean_text)
                        
                        logger.info(f"  Message from {participant}: {clean_text[:60]}...")
                        messages.append({"sender": participant, "content": clean_text})
                    except Exception:
                        continue
            except Exception as e:
                logger.warning(f"Failed to read thread {participant}: {e}")
                continue
    except Exception as e:
        logger.error(f"DM scrape error: {e}")
    return messages


async def _run_monitor(account_id: int, stop_event: threading.Event, target_profile_url: str = None):
    from playwright.async_api import async_playwright

    db: Session = SessionLocal()
    try:
        account = db.query(InstagramAccount).filter(InstagramAccount.id == account_id).first()
        if not account:
            return

        username = account.account_username
        try:
            password = decrypt(account.password_encrypted) if account.password_encrypted else ""
        except Exception:
            logger.error("Could not decrypt Instagram password")
            return

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            
            import os
            state_dir = "sessions"
            os.makedirs(state_dir, exist_ok=True)
            state_path = os.path.join(state_dir, f"account_{account_id}.json")
            
            if os.path.exists(state_path):
                context = await browser.new_context(storage_state=state_path)
                logger.info(f"Loaded existing session state for {username}")
            else:
                context = await browser.new_context()

            page = await context.new_page()

            # Check if already logged in by going to homepage
            # Check if already logged in by going to login page directly.
            # If already logged in, Instagram redirects to the feed.
            try:
                for retry in range(3):
                    try:
                        await page.goto("https://www.instagram.com/accounts/login/", timeout=30000)
                        break
                    except Exception as goto_err:
                        logger.warning(f"goto login retry {retry}: {goto_err}")
                        await page.wait_for_timeout(2000)
                
                await page.wait_for_timeout(3000)
                
                # --- Robust login state machine ---
                # Instagram shows 3 different screens depending on session state:
                # (A) Normal form: username + password inputs
                # (B) Saved profile: "Continue" button (no username input)
                # (C) Already logged in: redirected away from /accounts/login/
                
                if "login" not in page.url:
                    logger.info(f"Already logged in as {username} (redirected to {page.url})")
                else:
                    logger.info(f"Login required for {username}. Detecting login screen type...")
                    
                    # Delete the stale session file so we start fresh next time
                    if os.path.exists(state_path):
                        os.remove(state_path)
                        logger.info("Deleted stale session file.")
                    
                    # Check for cookie consent first
                    for cookie_text in ['Allow all cookies', 'Accept all cookies']:
                        btn = page.locator(f"button:has-text('{cookie_text}')")
                        if await btn.count() > 0:
                            logger.info(f"Accepting cookies: {cookie_text}")
                            await btn.first.click()
                            await page.wait_for_timeout(1500)
                            break
                    
                    # PHASE 1: Handle "Continue" button (saved profile screen)
                    continue_btn = page.locator("button:has-text('Continue')")
                    if await continue_btn.count() > 0 and await continue_btn.first.is_visible():
                        logger.info("Detected saved profile screen. Clicking 'Continue'...")
                        await continue_btn.first.click()
                        await page.wait_for_timeout(2500)
                    
                    # PHASE 2: Fill username if input is present (normal login form)
                    user_input = page.locator("input[name='username'], input[name='email']")
                    if await user_input.count() > 0 and await user_input.first.is_visible():
                        logger.info("Filling username...")
                        await user_input.first.fill(username)
                        await page.wait_for_timeout(500)
                    
                    # PHASE 3: Fill password (present after Continue click OR on normal form)
                    pass_input = page.locator("input[name='password'], input[name='pass']")
                    logger.info("Waiting for password input...")
                    await pass_input.first.wait_for(timeout=10000)
                    logger.info("Filling password...")
                    await pass_input.first.fill(password)
                    await page.wait_for_timeout(500)
                    
                    # Submit
                    logger.info("Submitting login...")
                    await pass_input.first.press("Enter")
                    await page.wait_for_timeout(2000)
                    
                    # Fallback button click
                    login_btn = page.locator("button:has-text('Log in'), button:has-text('Log In')")
                    if await login_btn.count() > 0 and await login_btn.first.is_visible():
                        logger.info("Clicking Log In button explicitly...")
                        await login_btn.first.click()
                    
                    # Wait up to 60s for the user to manually solve captcha/2FA if needed
                    logger.info("Waiting for login to complete... (If stuck, solve CAPTCHA/2FA in browser window!)")
                    for _ in range(60):
                        if "login" not in page.url:
                            break
                        await asyncio.sleep(1)
                    
                    if "login" in page.url:
                        logger.error(f"Login failed for {username} after 60s. Stopping monitor.")
                        await browser.close()
                        return
                    
                    logger.info(f"Instagram login succeeded for {username}")
                    await page.screenshot(path="instagram_login_success.png")
                    await context.storage_state(path=state_path)
            except Exception as e:
                logger.error(f"Instagram session check/login error: {e}")
                await browser.close()
                return

            # Monitoring loop
            while not stop_event.is_set():
                db.refresh(account)
                if is_session_expired(account):
                    logger.info(f"Session expired for account {account_id}")
                    break

                user = db.query(User).filter(User.id == account.user_id).first()
                if not user:
                    break

                # Important: After login, Instagram almost always shows the Notifications modal.
                # If we don't clear it before profile/post navigation, the scraper freezes.
                await _dismiss_modals(page)

                # Scrape profile posts
                try:
                    target = target_profile_url.strip() if target_profile_url and target_profile_url.strip() else f"https://www.instagram.com/{username}/"
                    if not target.startswith("http"):
                        target = f"https://www.instagram.com/{target.strip('/')}/"
                    logger.info(f"Navigating to posts profile: {target}")
                    
                    for goto_retry in range(3):
                        try:
                            await page.goto(target, timeout=40000)
                            break
                        except Exception as ge:
                            logger.warning(f"goto profile retry {goto_retry}: {ge}")
                            await page.wait_for_timeout(2000)
                    
                    await page.wait_for_timeout(4000)
                    # Dismiss any pop-ups on the profile page
                    await _dismiss_modals(page)
                    await page.wait_for_timeout(1000)
                    
                    # Scroll to load more posts
                    for _ in range(3):
                        await page.evaluate("window.scrollBy(0, 800)")
                        await page.wait_for_timeout(1000)
                    
                    post_links = await page.locator("a[href*='/p/']").all()
                    post_urls = []
                    for link in post_links[:20]:
                        try:
                            href = await link.get_attribute("href")
                            if href and "/p/" in href:
                                full_url = f"https://www.instagram.com{href}" if href.startswith("/") else href
                                if full_url not in post_urls:
                                    post_urls.append(full_url)
                        except Exception:
                            continue

                    logger.info(f"Found {len(post_urls)} post URLs to analyze for {target}")

                    for post_url in post_urls[:10]:  # Analyze up to 10 posts per cycle
                        try:
                            # Safely extract just the post ID ignoring query params or trailing slashes
                            post_id_str = post_url.split("/p/")[1].split("/")[0].split("?")[0]
                            existing_post = db.query(Post).filter(Post.instagram_post_id == post_id_str).first()
                            if not existing_post:
                                post = Post(
                                    instagram_post_id=post_id_str,
                                    account_id=account.id,
                                    post_url=post_url,
                                )
                                db.add(post)
                                db.commit()
                                db.refresh(post)
                                logger.info(f"  New post found: {post_url}")
                            else:
                                post = existing_post

                            # Scrape comments
                            # Ensure we dismiss any modals that pop up on the post page before scraping
                            await _dismiss_modals(page)
                            raw_comments = await _scrape_comments(page, post_url)
                            logger.info(f"  Got {len(raw_comments)} comments from {post_url}")
                            for c in raw_comments:
                                try:
                                    exists = db.query(Comment).filter(
                                        Comment.post_id == post.id,
                                        Comment.author == c["author"],
                                        Comment.content == c["content"]
                                    ).first()
                                    if not exists:
                                        comment = Comment(post_id=post.id, author=c["author"], content=c["content"])
                                        db.add(comment)
                                        db.commit()
                                        db.refresh(comment)
                                        # Run CPU-bound analysis in a thread pool so we don't
                                        # block the asyncio event loop while the ML model runs.
                                        loop = asyncio.get_event_loop()
                                        result = await loop.run_in_executor(
                                            None, analyze_content,
                                            user.id, "comment", comment.id, c["content"], c["author"]
                                        )
                                        logger.info(f"    Analyzed comment from @{c['author']}: score={result.get('toxicity_score', 0):.2f} cat={result.get('category', '?')}")
                                except Exception as ce:
                                    logger.warning(f"    Comment processing error: {ce}")
                                    continue
                        except Exception as post_err:
                            logger.warning(f"  Error processing post {post_url}: {post_err}")
                            continue

                except Exception as e:
                    logger.error(f"Post scrape error: {e}")

                # Scrape DMs
                try:
                    raw_dms = await _scrape_dms(page, username=username, password=password)
                    for dm in raw_dms:
                        conv = db.query(Conversation).filter(
                            Conversation.participant == dm["sender"]
                        ).first()
                        if not conv:
                            conv = Conversation(participant=dm["sender"])
                            db.add(conv)
                            db.commit()
                            db.refresh(conv)

                        exists = db.query(Message).filter(
                            Message.conversation_id == conv.id,
                            Message.sender == dm["sender"],
                            Message.content == dm["content"]
                        ).first()
                        if not exists:
                            msg = Message(
                                conversation_id=conv.id,
                                sender=dm["sender"],
                                receiver=username,
                                content=dm["content"],
                            )
                            db.add(msg)
                            db.commit()
                            db.refresh(msg)
                            # Run ML analysis without blocking the event loop
                            loop = asyncio.get_event_loop()
                            result = await loop.run_in_executor(
                                None, analyze_content,
                                user.id, "message", msg.id, dm["content"], dm["sender"]
                            )
                            # Update conversation risk
                            conv.message_count = (conv.message_count or 0) + 1
                            if result and result.get("toxicity_score", 0) > 0.3:
                                conv.flagged_count = (conv.flagged_count or 0) + 1
                            conv.risk_score = (conv.flagged_count / max(conv.message_count, 1)) * 100
                            db.commit()
                except Exception as e:
                    logger.error(f"DM scrape error: {e}")

                # Wait ~60s before next scan with some jitter to avoid patterns
                import random
                wait_time = 60 + random.randint(-10, 20)
                logger.info(f"Finished scraping cycle. Waiting {wait_time}s before next scan...")
                for _ in range(wait_time):
                    if stop_event.is_set():
                        break
                    await asyncio.sleep(1)

            await browser.close()

    except Exception as e:
        logger.error(f"Monitor error: {e}")
    finally:
        # Mark stopped
        account = db.query(InstagramAccount).filter(InstagramAccount.id == account_id).first()
        if account:
            account.monitoring_status = "stopped"
            db.commit()
        db.close()


def start_monitoring(account: InstagramAccount, target_profile_url: str = None):
    if cast(int, account.id) in _active_monitors:
        return
    stop_event = threading.Event()
    _active_monitors[cast(int, account.id)] = stop_event

    def run():
        import sys
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_run_monitor(cast(int, account.id), stop_event, target_profile_url))
        loop.close()
        _active_monitors.pop(cast(int, account.id), None)

    t = threading.Thread(target=run, daemon=True)
    t.start()


def stop_monitoring(account_id: int):
    ev = _active_monitors.get(account_id)
    if ev:
        ev.set()
        _active_monitors.pop(account_id, None)
