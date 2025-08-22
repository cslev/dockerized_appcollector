import json
import math
import os
import re
from typing import Optional
####  own classes ####
from libs.logger import CustomLogger
from scraper.agentql_scraper import AgentQLPlaywrightScraper
import database.models
import database.db_controller as db_controller


from libs import misc
## ---------------- ##
logger = CustomLogger("AppCollector")
HEADLESS=False

def extract_github_project_url(full_url: str) -> tuple[str, str, str]:
    """
    Extract the GitHub project URL, developer, and name from a full GitHub file URL using simple string splitting.
    
    Example:
    "https://github.com/blockscout/blockscout/blob/master/docker-compose/docker-compose.yml"
    -> ("blockscout", "blockscout", "https://github.com/blockscout/blockscout")
    
    Args:
        full_url (str): The full GitHub URL
        
    Returns:
        tuple[str, str, str]: A tuple containing (developer, name, project_url)
                             developer is the GitHub username or organization (e.g., "blockscout")
                             name is the repository name (e.g., "blockscout")
                             project_url is the extracted project URL, or the original URL if not a GitHub URL
    """
    if not full_url.startswith("https://github.com/"):
        # If not a GitHub URL, return empty developer, empty name, and original URL
        return ("", "", full_url)
    
    # Split by '/' and take first 5 parts: ['https:', '', 'github.com', 'owner', 'repo']
    parts = full_url.split('/')
    if len(parts) >= 5:
        project_url = '/'.join(parts[:5])  # "https://github.com/owner/repo"
        developer = parts[3]  # "owner"
        name = parts[4]  # "repo"
        return (developer, name, project_url)
    else:
        return ("", "", full_url)

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
num_pages=100

apps = scraper.search_query(url=google_url,
                            search_string=google_dork,
                            query=aql,
                            num_pages=num_pages)

# Process the results to extract GitHub project URLs
if apps:
  logger.info("=== PROCESSING RESULTS ===")
  
  # Create a single session for all database operations
  session = db_controller.get_session()
  try:
    for page_results in apps:
      if 'search_results' in page_results:
        for result in page_results['search_results']:
          if 'url' in result and result['url']:
            original_url = result['url']
            title = result['title']
            about = result['about']
            developer, name, project_url = extract_github_project_url(original_url)
            repo = db_controller.add_or_update_github_repository(session=session,
                                                          developer=developer,
                                                          name=name,
                                                          url=project_url,
                                                          about=about)
            logger.info(f"Added/Updated repository: {developer}/{name}")
    
    # Commit all changes at once
    session.commit()
    logger.info("All repository data committed to database")
    
  except Exception as e:
    logger.error(f"Error processing results: {e}")
    session.rollback()
    raise
  finally:
    # Always close the session when done
    session.close()
  logger.info(f"\n=== UNIQUE GITHUB PROJECTS FOUND ===")

