from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import asyncio
from scraper import scrape_agents, scrape_agent_profile, scrape_local_agents_page, AgentInfo
import re

app = FastAPI(
    title="OneReal Agent Scraper API",
    description="API to scrape agent information from onereal.com",
    version="1.0.0"
)


class ScrapeResponse(BaseModel):
    success: bool
    total_agents: int
    agents: List[AgentInfo]
    message: Optional[str] = None


class AgentVerificationRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    license: Optional[str] = None


class AgentVerificationResponse(BaseModel):
    match: bool
    message: str
    matched_agent: Optional[AgentInfo] = None
    provided_details: AgentVerificationRequest


@app.get("/")
async def root():
    return {
        "message": "OneReal Agent Scraper API",
        "endpoints": {
            "/scrape-agents": "Scrape all agents from search page",
            "/scrape-profile/{profile_id}": "Scrape specific agent profile",
            "/scrape-agents-full": "Scrape all agents with full detailed information (Playwright)",
            "/scrape-agents-full-mcp": "Scrape all agents with full detailed information (Playwright MCP fallback)",
            "/scrape-local-agents": "Scrape agents from local HTML page",
            "/verify-agent": "Verify agent details against website (Playwright)",
            "/verify-agent-mcp": "Verify agent details against website (Playwright MCP)",
            "/docs": "API documentation"
        }
    }


@app.get("/scrape-agents", response_model=ScrapeResponse)
async def get_all_agents(search_label: str = ""):
    """
    Scrape all agents from the search page.
    
    Args:
        search_label: Optional search parameter to filter agents
    
    Returns:
        List of all agents with their basic information
    """
    try:
        agents = await scrape_agents(search_label)
        return ScrapeResponse(
            success=True,
            total_agents=len(agents),
            agents=agents,
            message=f"Successfully scraped {len(agents)} agents"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scraping agents: {str(e)}")


@app.get("/scrape-profile/{profile_id}", response_model=AgentInfo)
async def get_agent_profile(profile_id: str):
    """
    Scrape detailed information for a specific agent profile.
    
    Args:
        profile_id: The agent's profile ID (e.g., 'aniraula')
    
    Returns:
        Detailed agent information
    """
    try:
        agent_info = await scrape_agent_profile(profile_id)
        if not agent_info:
            raise HTTPException(status_code=404, detail=f"Agent profile '{profile_id}' not found")
        return agent_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scraping profile: {str(e)}")


@app.get("/scrape-agents-full", response_model=ScrapeResponse)
async def get_all_agents_full(search_label: str = ""):
    """
    Scrape all agents from the search page AND get detailed information for each agent.
    This combines both /scrape-agents and /scrape-profile endpoints.
    
    Args:
        search_label: Optional search parameter to filter agents
    
    Returns:
        List of all agents with their complete detailed information
    """
    try:
        # First, get all agents from search page
        agents = await scrape_agents(search_label)
        
        if not agents:
            return ScrapeResponse(
                success=True,
                total_agents=0,
                agents=[],
                message="No agents found"
            )
        
        # Extract profile IDs from profile URLs
        detailed_agents = []
        failed_profiles = []
        
        # Process agents with limited concurrency to avoid overwhelming the server
        semaphore = asyncio.Semaphore(3)  # Process 3 at a time
        
        async def get_detailed_info(agent: AgentInfo):
            async with semaphore:
                try:
                    # Extract profile_id from profile_url
                    # URL format: https://onereal.com/profile/{profile_id}
                    profile_url = agent.profile_url or ""
                    match = re.search(r'/profile/([^/?]+)', profile_url)
                    if match:
                        profile_id = match.group(1)
                        
                        # Get detailed profile information
                        detailed_info = await scrape_agent_profile(profile_id)
                        
                        if detailed_info:
                            # Merge basic info with detailed info (detailed info takes precedence)
                            merged_info = AgentInfo(
                                name=detailed_info.name or agent.name,
                                location=detailed_info.location or agent.location,
                                profile_url=agent.profile_url,
                                phone=detailed_info.phone or agent.phone,
                                email=detailed_info.email or agent.email,
                                bio=detailed_info.bio or agent.bio,
                                specialties=detailed_info.specialties or agent.specialties,
                                languages=detailed_info.languages or agent.languages,
                                years_experience=detailed_info.years_experience or agent.years_experience,
                                image_url=detailed_info.image_url or agent.image_url,
                                office=detailed_info.office or agent.office,
                                license=detailed_info.license or agent.license,
                                website=detailed_info.website or agent.website,
                                facebook=detailed_info.facebook or agent.facebook,
                                instagram=detailed_info.instagram or agent.instagram
                            )
                            return merged_info
                    return agent  # Return basic info if profile_id extraction failed
                except Exception as e:
                    print(f"Error getting detailed info for {agent.profile_url}: {e}")
                    failed_profiles.append(agent.profile_url)
                    return agent  # Return basic info on error
        
        # Process all agents concurrently (with semaphore limit)
        tasks = [get_detailed_info(agent) for agent in agents]
        detailed_agents = await asyncio.gather(*tasks)
        
        message = f"Successfully scraped {len(detailed_agents)} agents with full details"
        if failed_profiles:
            message += f" ({len(failed_profiles)} profiles failed to load details)"
        
        return ScrapeResponse(
            success=True,
            total_agents=len(detailed_agents),
            agents=detailed_agents,
            message=message
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scraping agents with full details: {str(e)}")


@app.get("/scrape-agents-full-mcp", response_model=ScrapeResponse)
async def get_all_agents_full_mcp(search_label: str = ""):
    """
    Scrape all agents with full detailed information using Playwright MCP (fallback for regular Playwright).
    This endpoint uses Playwright MCP for browser automation.
    
    Args:
        search_label: Optional search parameter to filter agents
    
    Returns:
        List of all agents with their complete detailed information
    """
    try:
        from scraper_mcp import scrape_agents_full_mcp
        agents = await scrape_agents_full_mcp(search_label)
        return ScrapeResponse(
            success=True,
            total_agents=len(agents),
            agents=agents,
            message=f"Successfully scraped {len(agents)} agents with full details using Playwright MCP"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scraping agents with Playwright MCP: {str(e)}")


@app.get("/scrape-local-agents", response_model=ScrapeResponse)
async def get_local_agents(base_url: str = "https://dreproxy.onrender.com"):
    """
    Scrape agents from the HTML page at /static/index.html.
    This endpoint navigates to the page, clicks on "Agent List", and extracts all agent information.
    
    Args:
        base_url: Base URL of the server (default: https://dreproxy.onrender.com)
    
    Returns:
        List of all agents with their information from the page
    """
    try:
        agents = await scrape_local_agents_page(base_url)
        return ScrapeResponse(
            success=True,
            total_agents=len(agents),
            agents=agents,
            message=f"Successfully scraped {len(agents)} agents from page"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scraping agents: {str(e)}")


def normalize_string(s: Optional[str]) -> Optional[str]:
    """Normalize string for comparison (lowercase, strip whitespace)"""
    if not s:
        return None
    return s.lower().strip()


def normalize_phone(phone: Optional[str]) -> Optional[str]:
    """Normalize phone number for comparison (remove spaces, dashes, parentheses)"""
    if not phone:
        return None
    # Remove common phone formatting characters
    normalized = re.sub(r'[\s\-\(\)\+]', '', phone)
    return normalized.lower()


def normalize_email(email: Optional[str]) -> Optional[str]:
    """Normalize email for comparison"""
    if not email:
        return None
    return email.lower().strip()


def agent_matches(provided: AgentVerificationRequest, scraped: AgentInfo) -> bool:
    """
    Check if provided agent details match scraped agent details.
    Returns True if at least one field matches (name, email, phone, or license).
    """
    match_count = 0
    total_fields = 0
    
    # Check name match
    if provided.name:
        total_fields += 1
        provided_name = normalize_string(provided.name)
        scraped_name = normalize_string(scraped.name)
        if provided_name and scraped_name and provided_name == scraped_name:
            match_count += 1
    
    # Check email match
    if provided.email:
        total_fields += 1
        provided_email = normalize_email(provided.email)
        scraped_email = normalize_email(scraped.email)
        if provided_email and scraped_email and provided_email == scraped_email:
            match_count += 1
    
    # Check phone match
    if provided.phone:
        total_fields += 1
        provided_phone = normalize_phone(provided.phone)
        scraped_phone = normalize_phone(scraped.phone)
        if provided_phone and scraped_phone and provided_phone == scraped_phone:
            match_count += 1
    
    # Check license match
    if provided.license:
        total_fields += 1
        provided_license = normalize_string(provided.license)
        scraped_license = normalize_string(scraped.license)
        if provided_license and scraped_license and provided_license == scraped_license:
            match_count += 1
    
    # Match if at least one field matches and all provided fields match
    if total_fields == 0:
        return False
    
    # Strict matching: all provided fields must match
    return match_count == total_fields and match_count > 0


@app.post("/verify-agent", response_model=AgentVerificationResponse)
async def verify_agent(
    agent_details: AgentVerificationRequest = Body(...),
    base_url: str = "https://dreproxy.onrender.com"
):
    """
    Verify agent details against the website using regular Playwright.
    
    This endpoint:
    1. Accepts agent details (name, email, phone, license) in the request body
    2. Scrapes the website to get all agents
    3. Compares the provided details with scraped agents
    4. Returns match: true if found, match: false if not found
    
    Args:
        agent_details: Agent details to verify (name, email, phone, license)
        base_url: Base URL of the server (default: https://dreproxy.onrender.com)
    
    Returns:
        Verification response with match status and matched agent details if found
    """
    try:
        # Validate that at least one field is provided
        if not any([agent_details.name, agent_details.email, agent_details.phone, agent_details.license]):
            raise HTTPException(
                status_code=400,
                detail="At least one field (name, email, phone, or license) must be provided"
            )
        
        # Scrape agents from the website
        scraped_agents = await scrape_local_agents_page(base_url)
        
        # Check if any scraped agent matches the provided details
        matched_agent = None
        for agent in scraped_agents:
            if agent_matches(agent_details, agent):
                matched_agent = agent
                break
        
        if matched_agent:
            return AgentVerificationResponse(
                match=True,
                message="Agent details match found on website",
                matched_agent=matched_agent,
                provided_details=agent_details
            )
        else:
            return AgentVerificationResponse(
                match=False,
                message="Agent details not found on website",
                matched_agent=None,
                provided_details=agent_details
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying agent: {str(e)}")


@app.post("/verify-agent-mcp", response_model=AgentVerificationResponse)
async def verify_agent_mcp(
    agent_details: AgentVerificationRequest = Body(...),
    base_url: str = "https://dreproxy.onrender.com"
):
    """
    Verify agent details against the website using Playwright MCP.
    
    This endpoint:
    1. Accepts agent details (name, email, phone, license) in the request body
    2. Scrapes the website to get all agents using Playwright MCP
    3. Compares the provided details with scraped agents
    4. Returns match: true if found, match: false if not found
    
    Args:
        agent_details: Agent details to verify (name, email, phone, license)
        base_url: Base URL of the server (default: https://dreproxy.onrender.com)
    
    Returns:
        Verification response with match status and matched agent details if found
    """
    try:
        from scraper_mcp import scrape_local_agents_page_mcp
        
        # Validate that at least one field is provided
        if not any([agent_details.name, agent_details.email, agent_details.phone, agent_details.license]):
            raise HTTPException(
                status_code=400,
                detail="At least one field (name, email, phone, or license) must be provided"
            )
        
        # Scrape agents from the website using Playwright MCP
        scraped_agents = await scrape_local_agents_page_mcp(base_url)
        
        # Check if any scraped agent matches the provided details
        matched_agent = None
        for agent in scraped_agents:
            if agent_matches(agent_details, agent):
                matched_agent = agent
                break
        
        if matched_agent:
            return AgentVerificationResponse(
                match=True,
                message="Agent details match found on website (via Playwright MCP)",
                matched_agent=matched_agent,
                provided_details=agent_details
            )
        else:
            return AgentVerificationResponse(
                match=False,
                message="Agent details not found on website (via Playwright MCP)",
                matched_agent=None,
                provided_details=agent_details
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying agent with Playwright MCP: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

