import json
import math
import os
import re
from typing import Optional
####  own classes ####
from libs.logger import CustomLogger
from scraper.agentql_scraper import AgentQLPlaywrightScraper


from libs import misc
## ---------------- ##
logger = CustomLogger("AppCollector")
HEADLESS=False

def extract_github_project_url(full_url: str) -> str:
    """
    Extract the GitHub project URL from a full GitHub file URL using simple string splitting.
    
    Example:
    "https://github.com/blockscout/blockscout/blob/master/docker-compose/docker-compose.yml"
    -> "https://github.com/blockscout/blockscout"
    
    Args:
        full_url (str): The full GitHub URL
        
    Returns:
        str: The extracted project URL, or the original URL if not a GitHub URL
    """
    if not full_url.startswith("https://github.com/"):
        return full_url
    
    # Split by '/' and take first 5 parts: ['https:', '', 'github.com', 'owner', 'repo']
    parts = full_url.split('/')
    if len(parts) >= 5:
        return '/'.join(parts[:5])  # "https://github.com/owner/repo"
    else:
        return full_url

## init AgentQL scraper
# Set headless to False to look more human-like
# initiate scraper with default values that will be picked up from ENV variables
scraper = AgentQLPlaywrightScraper(headless=False)

aql="""
{
  search_results[]
  {
    title
    about
    url
  }
}
"""

# Google dork query to find docker-compose files on GitHub
# This query searches for GitHub repositories that contain a docker-compose.yml file.
# It can be used to find projects that use Docker for containerization.
google_dork="site:github.com inurl:docker-compose.yml"
google_url="https://www.google.com"
url_with_dork="https://www.google.com/search?q=site%3Agithub.com+inurl%3Adocker-compose.yml"
num_pages=2

apps = scraper.search_query(url=google_url,
                            search_string=google_dork,
                            query=aql,
                            num_pages=num_pages)

# Process the results to extract GitHub project URLs
if apps:
  logger.info("=== PROCESSING RESULTS ===")
  
  for page_results in apps:
    if 'search_results' in page_results:
      for result in page_results['search_results']:
        if 'url' in result and result['url']:
          original_url = result['url']
          title = result['title']
          about = result['about']
          project_url = extract_github_project_url(original_url)
          logger.info(f"Title:  {title}")
          logger.info(f"About:  {about}")
          logger.info(f"URL:  {project_url}")
          logger.info("---")       

  logger.info(f"\n=== UNIQUE GITHUB PROJECTS FOUND ===")

