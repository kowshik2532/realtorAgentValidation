from playwright.async_api import async_playwright, Browser, Page
from typing import List, Optional, Dict
import asyncio
import re
from pydantic import BaseModel


class AgentInfo(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    profile_url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    bio: Optional[str] = None
    specialties: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    years_experience: Optional[str] = None
    image_url: Optional[str] = None
    office: Optional[str] = None
    license: Optional[str] = None
    website: Optional[str] = None
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    # Add more fields as needed


async def scrape_agents(search_label: str = "") -> List[AgentInfo]:
    """
    Scrape all agents from the search page.
    
    Args:
        search_label: Optional search parameter
    
    Returns:
        List of AgentInfo objects
    """
    async with async_playwright() as p:
        # Configure browser launch for Render deployment
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--single-process']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        page.set_default_timeout(60000)  # Set default timeout to 60 seconds
        
        try:
            # Navigate to search page with longer timeout and more lenient wait strategy
            search_url = f"https://onereal.com/search-agent?search_label={search_label}"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait a bit for dynamic content to load
            await page.wait_for_timeout(3000)
            
            # Wait for agent cards to load with longer timeout
            try:
                await page.wait_for_selector("a[href*='/profile/']", timeout=30000)
            except Exception:
                # If selector not found, try to continue anyway - might be loaded differently
                pass
            
            # Scroll to load all agents (if lazy loading)
            await auto_scroll(page)
            
            # Extract all agent profile links with basic info from cards
            agent_data_list = await page.evaluate("""
                () => {
                    const agents = [];
                    const linkElements = Array.from(document.querySelectorAll('a[href*="/profile/"]'));
                    const seenUrls = new Set();
                    
                    linkElements.forEach(linkEl => {
                        // Get the href attribute
                        let href = linkEl.getAttribute('href');
                        if (!href) return;
                        
                        // Convert relative URLs to absolute
                        let fullUrl = href;
                        if (href.startsWith('/')) {
                            fullUrl = 'https://onereal.com' + href;
                        } else if (!href.startsWith('http')) {
                            fullUrl = 'https://onereal.com/' + href;
                        }
                        
                        // Skip if we've already seen this URL
                        if (seenUrls.has(fullUrl)) return;
                        seenUrls.add(fullUrl);
                        
                        // Find the card element containing this link
                        let card = linkEl;
                        for (let i = 0; i < 5; i++) {
                            card = card.parentElement;
                            if (!card) break;
                            if (card.classList.toString().includes('card') || 
                                card.classList.toString().includes('Card') ||
                                card.tagName === 'DIV') {
                                break;
                            }
                        }
                        
                        let name = null;
                        let location = null;
                        let imageUrl = null;
                        
                        // Try to get name from image alt attribute
                        const img = linkEl.querySelector('img');
                        if (img) {
                            if (img.alt) name = img.alt.trim();
                            if (img.src) imageUrl = img.src;
                            if (!imageUrl && img.getAttribute('data-src')) {
                                imageUrl = img.getAttribute('data-src');
                            }
                        }
                        
                        // Try to find location in nearby text elements
                        if (card) {
                            const textElements = card.querySelectorAll('div, span, p');
                            for (let el of textElements) {
                                const text = el.innerText ? el.innerText.trim() : '';
                                // Look for location patterns (City, State format)
                                if (text && /^[A-Z][a-z]+,\\s*[A-Z]{2}$/.test(text)) {
                                    location = text;
                                    break;
                                }
                            }
                        }
                        
                        agents.push({
                            profile_url: fullUrl,
                            name: name,
                            location: location,
                            image_url: imageUrl
                        });
                    });
                    
                    return agents;
                }
            """)
            
            agents = []
            for agent_data in agent_data_list:
                try:
                    # Extract profile ID from URL
                    profile_url = agent_data.get('profile_url', '')
                    if isinstance(profile_url, str):
                        profile_id = profile_url.split('/profile/')[-1].split('?')[0]
                    else:
                        continue
                    
                    agent_info = AgentInfo(
                        profile_url=profile_url,
                        name=agent_data.get('name'),
                        location=agent_data.get('location'),
                        image_url=agent_data.get('image_url')
                    )
                    agents.append(agent_info)
                except Exception as e:
                    print(f"Error processing agent data: {e}")
                    continue
            
            await browser.close()
            return agents
            
        except Exception as e:
            await browser.close()
            raise Exception(f"Error scraping agents: {str(e)}")


async def scrape_agent_profile(profile_id: str) -> Optional[AgentInfo]:
    """
    Scrape detailed information from a specific agent profile page.
    
    Args:
        profile_id: The agent's profile ID (e.g., 'aniraula')
    
    Returns:
        AgentInfo object with detailed information
    """
    async with async_playwright() as p:
        # Configure browser launch for Render deployment
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--single-process']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        page.set_default_timeout(60000)  # Set default timeout to 60 seconds
        
        try:
            profile_url = f"https://onereal.com/profile/{profile_id}"
            await page.goto(profile_url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait a bit for dynamic content to load
            await page.wait_for_timeout(3000)
            
            # Wait for profile content to load (more lenient)
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=30000)
            except Exception:
                pass  # Continue even if timeout
            
            # Extract agent information based on actual HTML structure
            agent_data = await page.evaluate("""
                () => {
                    const data = {};
                    
                    // Extract name - look for h1 or main heading, fallback to page title
                    const nameEl = document.querySelector('h1, h2, [class*="name"], [class*="Name"]');
                    if (nameEl && nameEl.innerText) {
                        data.name = nameEl.innerText.trim();
                    } else {
                        // Fallback to page title
                        const title = document.title;
                        if (title) {
                            data.name = title.trim();
                        }
                    }
                    
                    // Extract location - look for location text
                    const locationEl = document.querySelector('[class*="location"], [class*="Location"], [class*="address"]');
                    if (locationEl && locationEl.innerText) {
                        data.location = locationEl.innerText.trim();
                    }
                    
                    // Extract phone - from tel: link
                    const phoneEl = document.querySelector('a[href^="tel:"]');
                    if (phoneEl) {
                        const phoneText = phoneEl.innerText ? phoneEl.innerText.trim() : '';
                        const phoneHref = phoneEl.getAttribute('href') || '';
                        data.phone = phoneText || phoneHref.replace('tel:', '');
                    }
                    
                    // Extract email - from mailto: link (prefer href over text)
                    const emailLinks = document.querySelectorAll('a[href^="mailto:"]');
                    if (emailLinks.length > 0) {
                        // Try to find link with actual email in text, otherwise use first href
                        let foundEmail = null;
                        for (let link of emailLinks) {
                            const href = link.getAttribute('href') || '';
                            const emailFromHref = href.replace('mailto:', '');
                            const text = link.innerText ? link.innerText.trim() : '';
                            
                            // If text looks like an email, use it
                            if (text && text.includes('@') && !text.includes('Get In Touch')) {
                                foundEmail = text;
                                break;
                            }
                        }
                        // If no email found in text, use href from first link
                        if (!foundEmail && emailLinks[0]) {
                            const href = emailLinks[0].getAttribute('href') || '';
                            foundEmail = href.replace('mailto:', '');
                        }
                        data.email = foundEmail;
                    }
                    
                    // Extract license - find "License #:" text and get next sibling
                    const licenseSection = Array.from(document.querySelectorAll('*')).find(el => 
                        el.innerText && el.innerText.includes('License #:')
                    );
                    if (licenseSection) {
                        const licenseDiv = licenseSection.querySelector('.break-words');
                        if (licenseDiv) {
                            data.license = licenseDiv.innerText.trim();
                        }
                    }
                    
                    // Extract languages - find "Languages:" text
                    const langSpan = Array.from(document.querySelectorAll('span.font-telegraf')).find(el => 
                        el.innerText && el.innerText.includes('Languages:')
                    );
                    if (langSpan && langSpan.innerText) {
                        const langText = langSpan.innerText.trim();
                        data.languages = langText.replace('Languages:', '').trim().split(',').map(l => l.trim());
                    }
                    
                    // Extract website - from onereal.com link
                    const websiteEl = document.querySelector('a[href*="onereal.com"][target="_blank"]');
                    if (websiteEl) {
                        const websiteHref = websiteEl.getAttribute('href');
                        const websiteText = websiteEl.innerText ? websiteEl.innerText.trim() : '';
                        data.website = websiteHref || websiteText;
                    }
                    
                    // Extract Facebook link
                    const facebookEl = document.querySelector('a[href*="facebook.com"]');
                    if (facebookEl) {
                        data.facebook = facebookEl.getAttribute('href');
                    }
                    
                    // Extract Instagram link
                    const instagramEl = document.querySelector('a[href*="instagram.com"]');
                    if (instagramEl) {
                        data.instagram = instagramEl.getAttribute('href');
                    }
                    
                    // Extract bio/description
                    const bioEl = document.querySelector('[class*="bio"], [class*="Bio"], [class*="description"], [class*="about"]');
                    if (bioEl && bioEl.innerText) {
                        data.bio = bioEl.innerText.trim();
                    }
                    
                    // Extract image - look for profile images
                    const imgEl = document.querySelector('img[alt], img[class*="profile"], img[class*="avatar"]');
                    if (imgEl) {
                        data.image_url = imgEl.src || imgEl.getAttribute('data-src') || imgEl.getAttribute('src');
                    }
                    
                    // Extract specialties - find "My Specialities" section
                    const specialtySection = Array.from(document.querySelectorAll('*')).find(el => 
                        el.innerText && (el.innerText.includes('My Specialities') || el.innerText.includes('My Specialties'))
                    );
                    if (specialtySection) {
                        const specialtyItems = specialtySection.querySelectorAll('div, span, a');
                        if (specialtyItems.length > 0) {
                            data.specialties = Array.from(specialtyItems)
                                .map(el => el.innerText.trim())
                                .filter(text => text && text.length > 0 && !text.includes('My Specialities'));
                        }
                    }
                    
                    // Extract years of experience
                    const expEl = document.querySelector('[class*="experience"], [class*="Experience"], [class*="years"]');
                    if (expEl && expEl.innerText) {
                        data.years_experience = expEl.innerText.trim();
                    }
                    
                    // Extract office
                    const officeEl = document.querySelector('[class*="office"], [class*="Office"]');
                    if (officeEl && officeEl.innerText) {
                        data.office = officeEl.innerText.trim();
                    }
                    
                    return data;
                }
            """)
            
            # Create AgentInfo object
            agent_info = AgentInfo(
                name=agent_data.get('name'),
                location=agent_data.get('location'),
                profile_url=profile_url,
                phone=agent_data.get('phone'),
                email=agent_data.get('email'),
                bio=agent_data.get('bio'),
                specialties=agent_data.get('specialties'),
                languages=agent_data.get('languages'),
                years_experience=agent_data.get('years_experience'),
                image_url=agent_data.get('image_url'),
                office=agent_data.get('office'),
                license=agent_data.get('license'),
                website=agent_data.get('website'),
                facebook=agent_data.get('facebook'),
                instagram=agent_data.get('instagram')
            )
            
            await browser.close()
            return agent_info
            
        except Exception as e:
            await browser.close()
            raise Exception(f"Error scraping profile {profile_id}: {str(e)}")


async def auto_scroll(page: Page):
    """
    Automatically scroll the page to load lazy-loaded content.
    """
    await page.evaluate("""
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


async def scrape_local_agents_page(base_url: str = "https://dreproxy.onrender.com") -> List[AgentInfo]:
    """
    Scrape agents from the HTML page at /static/index.html.
    
    Args:
        base_url: Base URL of the server (default: https://dreproxy.onrender.com)
    
    Returns:
        List of AgentInfo objects extracted from the page
    """
    async with async_playwright() as p:
        # Configure browser launch for Render deployment
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--single-process']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        page.set_default_timeout(60000)
        
        try:
            # Navigate to the HTML page
            page_url = f"{base_url}/static/index.html"
            await page.goto(page_url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait a bit for page to load
            await page.wait_for_timeout(2000)
            
            # Click on "Agent List" if the link exists
            try:
                # Try multiple ways to find and click Agent List
                agent_list_selectors = [
                    'text=Agent List',
                    'text=📋 Agent List',
                    'a:has-text("Agent List")',
                    '[href*="agent"]',
                    'button:has-text("Agent List")'
                ]
                
                clicked = False
                for selector in agent_list_selectors:
                    try:
                        agent_list_link = page.locator(selector).first
                        if await agent_list_link.is_visible(timeout=3000):
                            await agent_list_link.click()
                            await page.wait_for_timeout(1000)
                            clicked = True
                            break
                    except Exception:
                        continue
                
                if not clicked:
                    # Try clicking by text content
                    await page.evaluate("""
                        () => {
                            const links = Array.from(document.querySelectorAll('a, button, div'));
                            const agentListLink = links.find(el => 
                                el.innerText && el.innerText.includes('Agent List')
                            );
                            if (agentListLink) {
                                agentListLink.click();
                            }
                        }
                    """)
                    await page.wait_for_timeout(1000)
            except Exception as e:
                print(f"Could not click Agent List: {e}")
                # Continue anyway - might already be on the list page
            
            # Wait for agents list to load - wait for "Loading agents..." to disappear
            print("Waiting for agents to load...")
            try:
                # Wait for loading text to disappear (up to 20 seconds)
                await page.wait_for_function(
                    "!document.body.innerText.includes('Loading agents...')",
                    timeout=20000
                )
                print("Loading text disappeared")
            except Exception as e:
                print(f"Loading text still present or timeout: {e}")
            
            # Wait additional time for agents to fully load (10-15 seconds as user mentioned)
            await page.wait_for_timeout(15000)
            print("Waited 15 seconds for agents to load")
            
            # Wait for agents list to be visible
            try:
                await page.wait_for_selector("#agents-list .agent-card, .agents-list .agent-card", timeout=10000)
                print("Found agent cards")
            except Exception:
                # Try alternative selectors
                try:
                    await page.wait_for_selector(".agent-card", timeout=10000)
                    print("Found agent cards with alternative selector")
                except Exception as e:
                    print(f"Could not find agent cards: {e}")
                    # Try to get any agent cards that might exist
                    pass
            
            # Scroll to ensure all agents are loaded
            await auto_scroll(page)
            await page.wait_for_timeout(2000)
            
            # Extract agent information from the page - simplified without regex
            agents_data = await page.evaluate("""() => {
                const agents = [];
                let agentCards = document.querySelectorAll('#agents-list .agent-card, .agents-list .agent-card, .agent-card');
                if (agentCards.length === 0) {
                    agentCards = document.querySelectorAll('div[class*="agent"], div[class*="card"]');
                }
                agentCards.forEach(card => {
                    const agent = {};
                    const nameEl = card.querySelector('h3, h2, h1, [class*="name"]');
                    if (nameEl && nameEl.innerText) {
                        agent.name = nameEl.innerText.trim();
                    }
                    const paragraphs = card.querySelectorAll('p, div, span');
                    paragraphs.forEach(p => {
                        const text = p.innerText || '';
                        const labelSpan = p.querySelector('.label');
                        if (labelSpan) {
                            const label = labelSpan.innerText.trim().toLowerCase();
                            const value = text.replace(labelSpan.innerText, '').trim();
                            if (label.includes('email')) {
                                agent.email = value;
                            } else if (label.includes('phone')) {
                                agent.phone = value;
                            } else if (label.includes('licence') || label.includes('license')) {
                                agent.license = value;
                            }
                        }
                    });
                    if (agent.name) {
                        agents.push(agent);
                    }
                });
                return agents;
            }""")
            
            print(f"Extracted {len(agents_data)} agents from page")
            
            # Convert to AgentInfo objects
            agents = []
            for agent_data in agents_data:
                try:
                    agent_info = AgentInfo(
                        name=agent_data.get('name'),
                        email=agent_data.get('email'),
                        phone=agent_data.get('phone'),
                        license=agent_data.get('license')
                    )
                    agents.append(agent_info)
                except Exception as e:
                    print(f"Error processing agent data: {e}")
                    continue
            
            await browser.close()
            return agents
            
        except Exception as e:
            await browser.close()
            raise Exception(f"Error scraping local agents page: {str(e)}")

