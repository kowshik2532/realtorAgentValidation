"""
Playwright MCP-based scraper for onereal.com
Uses Playwright MCP server for browser automation
"""
from playwright_mcp_client import PlaywrightMCPClient
from scraper import AgentInfo, scrape_agent_profile
from typing import List, Optional
import re
import asyncio
import json


async def scrape_agents_full_mcp(search_label: str = "") -> List[AgentInfo]:
    """
    Scrape all agents with full detailed information using Playwright MCP.
    
    Args:
        search_label: Optional search parameter
    
    Returns:
        List of AgentInfo objects with complete information
    """
    async with PlaywrightMCPClient() as mcp:
        try:
            # Navigate to search page
            search_url = f"https://onereal.com/search-agent?search_label={search_label}"
            await mcp.navigate(search_url)
            await mcp.wait_for_timeout(3000)
            
            # Wait for agent cards to load
            await mcp.wait_for_timeout(5000)
            
            # Wait for agent cards to be visible
            wait_script = """
            () => {
                // Wait for at least one profile link to appear
                const maxWait = 10000; // 10 seconds
                const startTime = Date.now();
                while (Date.now() - startTime < maxWait) {
                    const links = document.querySelectorAll('a[href*="/profile/"]');
                    if (links.length > 0) {
                        return true;
                    }
                    // Small delay
                    const end = Date.now() + 100;
                    while (Date.now() < end) {}
                }
                return false;
            }
            """
            await mcp.evaluate(wait_script)
            await mcp.wait_for_timeout(2000)
            
            # Scroll to load all agents (similar to regular scraper)
            await mcp.scroll_to_bottom()
            await mcp.wait_for_timeout(3000)  # Wait for any lazy-loaded content after scroll
            
            # Extract agent profile links using JavaScript - same as regular scraper
            extract_script = """
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
                    
                    // Extract name and image from the link
                    const img = linkEl.querySelector('img');
                    const name = img ? (img.alt || img.getAttribute('alt') || '') : '';
                    const imageUrl = img ? (img.src || img.getAttribute('src') || null) : null;
                    
                    agents.push({
                        url: fullUrl,
                        name: name,
                        imageUrl: imageUrl
                    });
                });
                
                return agents;
            }
            """
            
            # Get agent links
            script_result = await mcp.evaluate(extract_script)
            agent_links_data = []
            
            # Debug: Print raw result
            print(f"Script result type: {type(script_result)}")
            print(f"Script result keys: {list(script_result.keys()) if isinstance(script_result, dict) else 'not dict'}")
            
            # Parse result - MCP returns content in a specific format
            if isinstance(script_result, dict):
                content = script_result.get("content", [])
                print(f"Content items: {len(content)}")
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        try:
                            text_content = item.get("text", "")
                            print(f"Text content length: {len(text_content)}, first 200 chars: {text_content[:200]}")
                            # Try parsing as JSON
                            data = json.loads(text_content)
                            print(f"Parsed data type: {type(data)}")
                            if isinstance(data, list):
                                agent_links_data = data
                                print(f"✅ Found {len(agent_links_data)} agents from list")
                            elif isinstance(data, dict) and "result" in data:
                                # If result is wrapped
                                result_data = data.get("result")
                                if isinstance(result_data, list):
                                    agent_links_data = result_data
                                    print(f"✅ Found {len(agent_links_data)} agents from wrapped result")
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}")
                            # If not JSON, might be a direct list string
                            try:
                                # Try to eval if it's a JavaScript array string
                                if text_content.strip().startswith('['):
                                    import ast
                                    agent_links_data = ast.literal_eval(text_content)
                                    print(f"✅ Found {len(agent_links_data)} agents from ast.literal_eval")
                            except Exception as e2:
                                print(f"ast.literal_eval error: {e2}")
                        except Exception as e:
                            print(f"Error parsing script result: {e}")
                            import traceback
                            traceback.print_exc()
            
            print(f"Final: Found {len(agent_links_data)} agent links from search page")
            
            if not agent_links_data:
                # Fallback: try to get HTML and parse it
                content_result = await mcp.get_content()
                if isinstance(content_result, dict):
                    content = content_result.get("content", [])
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            html = item.get("text", "")
                            # Extract profile links from HTML
                            link_pattern = r'href=["\'](/profile/[^"\']+)["\']'
                            matches = re.findall(link_pattern, html)
                            seen_urls = set()
                            for match in matches:
                                if match.startswith('/profile/'):
                                    profile_id = match.split('/profile/')[-1].split('?')[0]
                                    full_url = f"https://onereal.com/profile/{profile_id}"
                                    if full_url not in seen_urls:
                                        seen_urls.add(full_url)
                                        agent_links_data.append({
                                            "url": full_url,
                                            "name": None,
                                            "imageUrl": None
                                        })
            
            # Now get detailed info for each agent
            detailed_agents = []
            semaphore = asyncio.Semaphore(3)
            
            async def get_detailed_info(agent_data: dict):
                async with semaphore:
                    try:
                        profile_url = agent_data.get("url", "")
                        match = re.search(r'/profile/([^/?]+)', profile_url)
                        if not match:
                            return None
                        
                        profile_id = match.group(1)
                        
                        # Use the existing scrape_agent_profile function instead of navigating
                        # This uses a separate browser instance and is more reliable
                        detailed_info = await scrape_agent_profile(profile_id)
                        
                        if detailed_info:
                            # Merge basic info with detailed info
                            merged_info = AgentInfo(
                                name=detailed_info.name or agent_data.get("name"),
                                location=detailed_info.location,
                                profile_url=profile_url,
                                phone=detailed_info.phone,
                                email=detailed_info.email,
                                bio=detailed_info.bio,
                                specialties=detailed_info.specialties,
                                languages=detailed_info.languages,
                                years_experience=detailed_info.years_experience,
                                image_url=detailed_info.image_url or agent_data.get("imageUrl"),
                                office=detailed_info.office,
                                license=detailed_info.license,
                                website=detailed_info.website,
                                facebook=detailed_info.facebook,
                                instagram=detailed_info.instagram
                            )
                            return merged_info
                        else:
                            # Return basic info if detailed scrape failed
                            return AgentInfo(
                                name=agent_data.get("name"),
                                profile_url=profile_url,
                                image_url=agent_data.get("imageUrl")
                            )
                    except Exception as e:
                        print(f"Error getting detailed info for {agent_data.get('url')}: {e}")
                        # Return basic info on error
                        return AgentInfo(
                            name=agent_data.get("name"),
                            profile_url=agent_data.get("url"),
                            image_url=agent_data.get("imageUrl")
                        )
            
            # Process all agents
            print(f"Processing {len(agent_links_data)} agents for detailed info...")
            tasks = [get_detailed_info(agent_data) for agent_data in agent_links_data]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out None results and exceptions
            detailed_agents = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"Exception for agent {i}: {result}")
                elif result is not None:
                    detailed_agents.append(result)
                else:
                    print(f"Agent {i} returned None")
            
            print(f"Successfully processed {len(detailed_agents)} out of {len(agent_links_data)} agents")
            return detailed_agents
            
        except Exception as e:
            raise Exception(f"Error scraping agents with Playwright MCP: {str(e)}")


async def scrape_local_agents_page_mcp(base_url: str = "https://dreproxy.onrender.com") -> List[AgentInfo]:
    """
    Scrape agents from the HTML page at /static/index.html using Playwright MCP.
    
    Args:
        base_url: Base URL of the server (default: https://dreproxy.onrender.com)
    
    Returns:
        List of AgentInfo objects extracted from the page
    """
    async with PlaywrightMCPClient() as mcp:
        try:
            # Navigate to the HTML page
            page_url = f"{base_url}/static/index.html"
            await mcp.navigate(page_url)
            await mcp.wait_for_timeout(2000)
            
            # Click on "Agent List" if the link exists
            try:
                # Try clicking Agent List using multiple selectors
                agent_list_clicked = False
                selectors = [
                    'text=Agent List',
                    'text=📋 Agent List',
                    'a:has-text("Agent List")',
                    'button:has-text("Agent List")'
                ]
                
                for selector in selectors:
                    try:
                        await mcp.click(selector)
                        await mcp.wait_for_timeout(1000)
                        agent_list_clicked = True
                        break
                    except:
                        continue
                
                if not agent_list_clicked:
                    # Try JavaScript click
                    click_script = """
                    () => {
                        const links = Array.from(document.querySelectorAll('a, button, div'));
                        const agentListLink = links.find(el => 
                            el.innerText && el.innerText.includes('Agent List')
                        );
                        if (agentListLink) {
                            agentListLink.click();
                            return true;
                        }
                        return false;
                    }
                    """
                    await mcp.evaluate(click_script)
                    await mcp.wait_for_timeout(1000)
            except Exception as e:
                print(f"Could not click Agent List: {e}")
            
            # Wait for agents to load
            print("Waiting for agents to load...")
            wait_script = """
            () => {
                const maxWait = 20000; // 20 seconds
                const startTime = Date.now();
                while (Date.now() - startTime < maxWait) {
                    if (!document.body.innerText.includes('Loading agents...')) {
                        return true;
                    }
                    const end = Date.now() + 100;
                    while (Date.now() < end) {}
                }
                return false;
            }
            """
            await mcp.evaluate(wait_script)
            await mcp.wait_for_timeout(15000)  # Wait additional 15 seconds
            
            # Scroll to ensure all agents are loaded
            await mcp.scroll_to_bottom()
            await mcp.wait_for_timeout(2000)
            
            # Extract agent information from the page
            extract_script = """
            () => {
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
                        } else {
                            // Try to extract from text without label
                            const lowerText = text.toLowerCase();
                            if (lowerText.includes('email:')) {
                                const idx = lowerText.indexOf('email:');
                                if (idx >= 0) {
                                    let afterEmail = text.substring(idx + 6).trim();
                                    const newlineIdx = afterEmail.indexOf('\\n');
                                    const crIdx = afterEmail.indexOf('\\r');
                                    let endIdx = afterEmail.length;
                                    if (newlineIdx >= 0 && newlineIdx < endIdx) endIdx = newlineIdx;
                                    if (crIdx >= 0 && crIdx < endIdx) endIdx = crIdx;
                                    agent.email = afterEmail.substring(0, endIdx).trim();
                                }
                            }
                            if (lowerText.includes('phone:')) {
                                const idx = lowerText.indexOf('phone:');
                                if (idx >= 0) {
                                    let afterPhone = text.substring(idx + 6).trim();
                                    const newlineIdx = afterPhone.indexOf('\\n');
                                    const crIdx = afterPhone.indexOf('\\r');
                                    let endIdx = afterPhone.length;
                                    if (newlineIdx >= 0 && newlineIdx < endIdx) endIdx = newlineIdx;
                                    if (crIdx >= 0 && crIdx < endIdx) endIdx = crIdx;
                                    agent.phone = afterPhone.substring(0, endIdx).trim();
                                }
                            }
                            if (lowerText.includes('licence:') || lowerText.includes('license:')) {
                                let idx = lowerText.indexOf('licence:');
                                if (idx < 0) idx = lowerText.indexOf('license:');
                                if (idx >= 0) {
                                    let afterLicense = text.substring(idx + 8).trim();
                                    const newlineIdx = afterLicense.indexOf('\\n');
                                    const crIdx = afterLicense.indexOf('\\r');
                                    let endIdx = afterLicense.length;
                                    if (newlineIdx >= 0 && newlineIdx < endIdx) endIdx = newlineIdx;
                                    if (crIdx >= 0 && crIdx < endIdx) endIdx = crIdx;
                                    agent.license = afterLicense.substring(0, endIdx).trim();
                                }
                            }
                        }
                    });
                    if (agent.name) {
                        agents.push(agent);
                    }
                });
                return agents;
            }
            """
            
            script_result = await mcp.evaluate(extract_script)
            agents_data = []
            
            # Parse result
            if isinstance(script_result, dict):
                content = script_result.get("content", [])
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        try:
                            data = json.loads(item.get("text", ""))
                            if isinstance(data, list):
                                agents_data = data
                        except:
                            pass
            
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
            
            return agents
            
        except Exception as e:
            raise Exception(f"Error scraping local agents page with Playwright MCP: {str(e)}")
