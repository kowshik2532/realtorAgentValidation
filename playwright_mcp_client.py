"""
Playwright MCP Client - Direct Playwright implementation
Uses Playwright directly (already installed) as a fallback alternative
"""
from playwright.async_api import async_playwright, Page, Browser
from typing import Dict, Any, Optional
import asyncio
import json


class PlaywrightMCPClient:
    """Client that uses Playwright directly (MCP-like interface)"""
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        # Configure browser launch for Render deployment
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--single-process']
        )
        context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = await context.new_page()
        self.page.set_default_timeout(60000)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def navigate(self, url: str, browser_id: Optional[str] = None) -> Dict:
        """Navigate to a URL"""
        if not self.page:
            raise Exception("Page not initialized")
        await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await self.page.wait_for_timeout(1000)
        return {"success": True, "url": url}
    
    async def get_content(self, selector: Optional[str] = None, browser_id: Optional[str] = None) -> Dict:
        """Get page content"""
        if not self.page:
            raise Exception("Page not initialized")
        
        if selector:
            element = await self.page.query_selector(selector)
            if element:
                html = await element.inner_html()
                text = await element.inner_text()
            else:
                html = ""
                text = ""
        else:
            html = await self.page.content()
            text = await self.page.inner_text("body")
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"html": html, "text": text})
                }
            ]
        }
    
    async def click(self, selector: str, browser_id: Optional[str] = None) -> Dict:
        """Click an element"""
        if not self.page:
            raise Exception("Page not initialized")
        await self.page.click(selector, timeout=10000)
        await self.page.wait_for_timeout(500)
        return {"success": True}
    
    async def wait_for_timeout(self, milliseconds: int):
        """Wait for specified time"""
        await asyncio.sleep(milliseconds / 1000.0)
    
    async def evaluate(self, script: str, browser_id: Optional[str] = None) -> Any:
        """Evaluate JavaScript in the page"""
        if not self.page:
            raise Exception("Page not initialized")
        result = await self.page.evaluate(script)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result) if result is not None else "null"
                }
            ]
        }
    
    async def scroll_to_bottom(self):
        """Scroll to bottom of page to load lazy content"""
        if not self.page:
            raise Exception("Page not initialized")
        await self.page.evaluate("""
            async () => {
                await new Promise((resolve) => {
                    let totalHeight = 0;
                    const distance = 100;
                    const timer = setInterval(() => {
                        const scrollHeight = document.body.scrollHeight;
                        window.scrollBy(0, distance);
                        totalHeight += distance;
                        
                        if (totalHeight >= scrollHeight) {
                            clearInterval(timer);
                            resolve();
                        }
                    }, 100);
                });
            }
        """)

