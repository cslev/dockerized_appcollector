import os
import agentql
from playwright.sync_api import sync_playwright
import json
import re
import os
import time
import sys
from typing import Optional, List, Dict
from dotenv import load_dotenv
# import paginate tool from agentql tools
from agentql.tools.sync_api import paginate
from urllib.parse import urlparse
import random

current_dir = os.path.abspath(os.path.dirname(__file__))
src_dir= os.path.abspath(os.path.join(current_dir, '..'))
# set sys_path to also look for libs elsewhere
sys.path.append(src_dir)
from libs.logger import CustomLogger
from libs import misc


class AgentQLPlaywrightScraper:
  def __init__(self, 
                api_key: Optional[str] = None,
                headless: bool = False,
                proxy_address: Optional[str] = None,
                user_data_dir: str = "/tmp/playwright-user-data"):
    """
      Initialize the AgentQLScraper with your API key.

      Args:
        headless (bool): whether we want to see the browser or not
        proxy_address (str): the actual Tor proxy address
        user_data_dir (str): directory to persist browser session data
    """ 
    self.base_headers = {
        # Realistic User-Agent for Chrome on Windows
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        # Standard Accept header for HTML documents
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",   
        # Prioritize US English, then generic English
        "Accept-Language": "en-US,en;q=0.9",
        # Common Accept-Encoding for compression
        "Accept-Encoding": "gzip, deflate, br, zstd",
        # Keep-alive for persistent connections
        "Connection": "keep-alive",
        # Request secure connection if possible
        "Upgrade-Insecure-Requests": "1",
        # Additional headers to look more like a real browser
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0"
    }
        
    self.logger = CustomLogger(self.__class__.__name__)
    
    # Try to load environment variables from .env file if they don't exist
    if "AGENTQL_API_KEY" not in os.environ:
        self.logger.info("AGENTQL_API_KEY not found in environment, trying to load from .env file...")
        load_dotenv()
    
    try:
      api_key = os.environ["AGENTQL_API_KEY"]
    except KeyError as e:
      self.logger.warning("No API key is set to for AgentQL...checking function argument...")
      if api_key is not None:
        self.logger.info("API key found as function argument...setting it as ENV for AgentQL")
        os.environ["AGENTQL_API_KEY"] = api_key
      else:
        self.logger.error("No API key was found at all for AgentQL...exiting")
        exit(-1)
    
    self.headless = headless
    self.proxy_address = proxy_address
    self.user_data_dir = user_data_dir if user_data_dir is not None else "/tmp/playwright-user-data"
    self.logger.info("Initiated with API_KEY")

    self.playwright = sync_playwright().start()

    # create new context
    self._create_new_context()
    
    # --- ADD BASE HEADERS HERE ---
    # This will apply the base headers to all requests made within this persistent context
    # and all pages created from it.
    try:
      self.context.set_extra_http_headers(self.base_headers)
      self.logger.info("Base HTTP headers set for the browser context.")
    except Exception as e:
      self.logger.warning(f"Could not set headers (might be read-only context): {e}")
    
    # Get existing page or create new one
    if len(self.context.pages) > 0:
      self.page = self.context.pages[0]
      self.logger.info("Using existing page from browser context")
    else:
      self.page = self.context.new_page()
      self.logger.info("Created new page in browser context")

  
  def _create_new_context(self):
    """Create a new persistent browser context with anti-detection features"""
    self.logger.info("Creating new persistent browser context with anti-detection...")
    
    # Browser arguments to look more like a real browser
    args = [
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--disable-ipc-flooding-protection',
        '--disable-renderer-backgrounding',
        '--disable-backgrounding-occluded-windows',
        '--disable-background-timer-throttling',
        '--disable-features=TranslateUI',
        '--disable-features=VizDisplayCompositor',
        '--no-first-run',
        '--no-default-browser-check',
        '--no-sandbox',
        '--disable-web-security',
        '--disable-extensions-except',
        '--disable-plugins-discovery',
        '--start-maximized'
    ]
    
    # Create context with realistic browser settings
    self.context = self.playwright.chromium.launch_persistent_context(
        self.user_data_dir,
        headless=self.headless,
        args=args,
        viewport={'width': 1920, 'height': 1080},
        user_agent=self.base_headers["User-Agent"],
        locale='en-US',
        timezone_id='America/New_York',
        extra_http_headers=self.base_headers,
        ignore_https_errors=True,
        java_script_enabled=True,
        accept_downloads=True,
        bypass_csp=True,
        color_scheme='light'
    )
    
    # Get the default page
    if len(self.context.pages) > 0:
        self.page = self.context.pages[0]
    else:
        self.page = self.context.new_page()
    
    # Add anti-detection JavaScript
    self._add_stealth_scripts()

  def _add_stealth_scripts(self):
    """Add JavaScript to make the browser appear more human-like"""
    stealth_js = """
    // Remove webdriver property
    Object.defineProperty(navigator, 'webdriver', {
      get: () => undefined,
    });

    // Mock languages and plugins
    Object.defineProperty(navigator, 'languages', {
      get: () => ['en-US', 'en'],
    });

    Object.defineProperty(navigator, 'plugins', {
      get: () => [1, 2, 3, 4, 5],
    });

    // Mock screen resolution
    Object.defineProperty(screen, 'width', {
      get: () => 1920,
    });
    Object.defineProperty(screen, 'height', {
      get: () => 1080,
    });

    // Add some randomness to mouse movements
    const originalAddEventListener = EventTarget.prototype.addEventListener;
    EventTarget.prototype.addEventListener = function(type, listener, options) {
      if (type === 'mousemove') {
        const newListener = function(e) {
          setTimeout(() => listener(e), Math.random() * 100);
        };
        return originalAddEventListener.call(this, type, newListener, options);
      }
      return originalAddEventListener.call(this, type, listener, options);
    };
    """
    
    self.page.add_init_script(stealth_js)
    self.logger.debug("Anti-detection scripts added")

  def _simulate_human_behavior(self):
    """Simulate human-like behavior on the page"""
    try:
        # Random mouse movements
        for _ in range(random.randint(2, 5)):
            x = random.randint(100, 1800)
            y = random.randint(100, 900)
            self.page.mouse.move(x, y)
            time.sleep(random.uniform(0.1, 0.5))
        
        # Random scroll
        scroll_amount = random.randint(100, 500)
        self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        time.sleep(random.uniform(0.5, 1.5))
        
        # Scroll back up a bit
        scroll_back = random.randint(50, 200)
        self.page.evaluate(f"window.scrollBy(0, -{scroll_back})")
        time.sleep(random.uniform(0.3, 1.0))
        
    except Exception as e:
        self.logger.debug(f"Error in human behavior simulation: {e}")

  def _human_type(self, element, text):
    """Type text with human-like delays"""
    try:
        # Clear the field first
        element.clear()
        time.sleep(random.uniform(0.2, 0.5))
        
        # Type each character with random delays
        for char in text:
            element.type(char)
            # Random delay between keystrokes (mimics human typing)
            delay = random.uniform(0.05, 0.3)
            if char == ' ':
                delay = random.uniform(0.1, 0.5)  # Longer pause at spaces
            time.sleep(delay)
            
    except Exception as e:
        self.logger.debug(f"Error in human typing: {e}")
        # Fallback to regular fill
        element.fill(text)

  def close(self):
    """
    Closing browser and playwright
    Note: If connected to existing browser, this will only close our connection,
    not the actual browser (which is what we want)
    """
    self.logger.info("Closing browser connection and Playwright")
    try:
      self.logger.info("Closing our own browser instance")
      self.context.close()
    except Exception as e:
      self.logger.warning(f"Error during browser close: {e}")
    finally:
      try:
        self.playwright.stop()
      except Exception as e:
        self.logger.warning(f"Error stopping Playwright: {e}")



  def paginate_query(self, 
                     url: str, 
                     query: str, 
                     max_pages: int = 1,
                     agentql_query_timeout=60000,
                     referer: Optional[str] = None,
                     new_tab: bool = False) -> list:
    """
    Loads the page, runs the AgentQL query, and paginates through up to max_pages.
    Returns a list of results aggregated from all pages.
    Args:
      url (str): The base URL to load and start the query process.
      query (str): AgentQL query
      max_pages (int, optional): The maximum number of pages to paginate through. Defaults to 1.
      close_browser_on_finish (bool, optional): Whether to close the browser after pagination is complete. Defaults to True.
      referer (str, optional): The HTTP-REREFER string to be set for the browser. If not set the base URL will be used
      new_tab (bool, optional): Open a new tab for the URL to be scraped (default: False)
    Returns:
      list: Aggregated results from all pages, or an empty list on error
    """
    try:
      if not referer:
        self.logger.info("REFERER was not set, let's use the base URL then as a referer...")
        parsed_url = urlparse(url)
        referer = f"{parsed_url.scheme}://{parsed_url.netloc}"

      headers_for_this_navigation = {**self.base_headers, "Referer": referer}
      self.logger.debug(f"Extra headers set for this query:\n{headers_for_this_navigation}")

      current_page = None # Initialize to None for scope
      agql_page = None # Initialize agql_page for broader scope

      if new_tab:
        self.logger.debug("Page will be opened in a new tab!")
        current_page = self.context.new_page() # Assign to current_page
        current_page.set_extra_http_headers(headers_for_this_navigation)
        self.logger.debug(f"Waiting for the page to be loaded completely...")
        current_page.goto(url, wait_until="load", timeout=agentql_query_timeout)
        current_page.wait_for_load_state("domcontentloaded") 
        self.logger.debug(f"domcontentLoaded event fired")
        agql_page = agentql.wrap(current_page) # Assign to agql_current_page
      else:
        self.context.set_extra_http_headers(headers_for_this_navigation)
        self.logger.debug(f"Opening page in existing tab: {url}")
        self.logger.debug(f"Waiting for the page to be loaded completely...")
        self.page.goto(url,  wait_until="load", timeout=agentql_query_timeout)
        self.page.wait_for_load_state("domcontentloaded") # Wait for 'domcontentloaded'
        self.logger.debug(f"domcontentLoaded event fired")
        agql_page = agentql.wrap(self.page)
        current_page = self.page # Keep track of the current Playwright page object

      agql_page.wait_for_page_ready_state(True)
      self.logger.debug(f"Page ready state reported for {url}")

      self.logger.debug(f"[DONE]...but let's wait 2 more seconds")
      agql_page.wait_for_timeout(2000)  # Waits 2 seconds

      # do some human actions like scrolling and random mouse movement
      self.mimic_human_actions(current_page)

      self.logger.info(f"Collecting data over {max_pages} pages: {url}")
      if max_pages is None:
        self.logger.warning("Pagination depth was not defined...reverting it to 1")
        max_pages = 1
      self.logger.info(f"###################################################################")
      self.logger.info(f"Scraping started at {misc.get_current_time()} with timeout of {agentql_query_timeout} for {max_pages} page(s)")
      self.logger.info(f"Be patient ah!")
      self.logger.info(f"###################################################################")
      paginated_data = paginate(page=agql_page, 
              query=query, 
              number_of_pages=max_pages, 
              timeout=agentql_query_timeout
              )
      return paginated_data
    except Exception as e:
      self.logger.error(f"AgentQL paginated query failed\n{e}", exc_info=True)
      return []
    finally:
      if new_tab and current_page:
        self.logger.debug("Closing tab...sleeping for 2 seconds")
        current_page.close()
        time.sleep(2)
    # If for some reason the try block does not return, always return a list
  # End of paginate_query


  def search_query(self,
                   url: str,
                   search_string: str,
                   query: str,
                   num_pages: int) -> List[Dict]:
    """
    Given a URL and a search string, 
    this method will look for the search field and button on the page,
    type in the search string, and click the search button.
    
    This is useful for automating searches on websites like Google, Bing, 
    or any site with a search functionality.
    
    Args:
      url (str): The URL of the web page to navigate to
      search_string (str): The search query/term to enter in the search field
      query (str): The AgentQL query to run after the search is performed
      num_pages (int): The number of pages to paginate through after the search
      
    Returns:
      List[Dict]: List of dictionaries containing search results from all pages,
                  or empty list if search failed or no results found
      
    Raises:
      Exception: If the search field or button cannot be found on the page
    """
    SEARCH_FIELD_QUERY="""
    {
      search_query
      search_button
    }
    """
    try:
      self.logger.debug(f"Opening page: {url}")
      
      # Add random delay before navigation
      random_delay = random.uniform(2, 5)
      self.logger.debug(f"Waiting {random_delay:.2f}s before navigation...")
      time.sleep(random_delay)
      
      self.page.goto(url, wait_until="domcontentloaded")
      
      # Random delay after page load
      page_load_delay = random.uniform(3, 7)
      self.logger.debug(f"Page loaded, waiting {page_load_delay:.2f}s...")
      time.sleep(page_load_delay)
      
      # Simulate human-like mouse movement
      self._simulate_human_behavior()
      
      self.logger.debug("Wrapping playwright page for agentQL querying")
      agql_page = agentql.wrap(self.page)
      
      self.logger.debug("Looking for search field and button...")
      response = agql_page.query_elements(SEARCH_FIELD_QUERY)
      
      if response.search_query and response.search_button:
        # Click on the search field first (more human-like)
        self.logger.debug("Clicking on search field...")
        response.search_query.click()
        time.sleep(random.uniform(1, 2))
        
        # Type with human-like delays
        self.logger.debug(f"Typing search string: {search_string}")
        self._human_type(response.search_query, search_string)
        
        # Random delay before clicking search
        search_delay = random.uniform(1, 3)
        self.logger.debug(f"Waiting {search_delay:.2f}s before searching...")
        time.sleep(search_delay)
        
        self.logger.debug("Clicking search button...")
        response.search_button.click()
        
        # Wait for the search results to load
        self.page.wait_for_load_state("domcontentloaded")
        self.logger.debug("Search completed successfully")
        
        # Additional wait with some randomness
        result_wait = random.uniform(3, 6)
        self.logger.debug(f"Waiting {result_wait:.2f}s for results to fully load...")
        time.sleep(result_wait)
        
        # Wrap the page for AgentQL querying after search
        agql_page = agentql.wrap(self.page)

        paginated_data = paginate(page=agql_page, 
                                  query=query, 
                                  number_of_pages=num_pages)
        if paginated_data:
            return paginated_data
        else:
            self.logger.warning("No data returned from pagination")
            return []
      else:
        self.logger.error("Search field or button not found on the page")
        return []
          
    except Exception as e:
      self.logger.error(f"Error during search: {e}")
      return []



  def query(self, 
            url: str, 
            query: str,
            elements:bool=False):
    """
    Loads the specified web page in a Playwright browser (either headless or with head),
    wraps the page for AgentQL querying, executes the provided AgentQL query,
    and returns the extracted data as a Python dictionary.

    Args:
      url (str): The URL of the web page to scrape.
      query (str): The AgentQL query string to execute on the page.
      elements (bool): Indicate whether to gather the HTML element instead of the content
    Returns:
      dict: The structured data extracted from the page.
    """
    self.logger.debug(f"Opening page: {url}")
    self.page.goto(url)
    
    self.logger.debug("Wrapping playwright page for agentQL querying")
    agql_page = agentql.wrap(self.page)  # Wrap Playwright page for AgentQL querying
    self.logger.debug("Running AgentQL query...")
    if elements:
      result = agql_page.query_elements(query)
    else:
      result = agql_page.query_data(query)

    return result

  def scroll_page_down(self, 
                       steps:int=5, 
                       delay_per_step:int=100,
                       page=None,
                       random_offset_range=(-200, 200)) -> None:
    """Scrolls down the page using mouse wheel simulation."""
    if not page:
      self.logger.warning("No page object was passed to scroll_page_down()")
      return
    
    try:
      # Get page dimensions
      page_info = page.evaluate("""
          () => {
              return {
                  scrollHeight: document.body.scrollHeight,
                  clientHeight: window.innerHeight,
                  currentScrollTop: window.pageYOffset
              };
          }
      """)
      
      max_scroll = page_info['scrollHeight'] - page_info['clientHeight']
      current_scroll = page_info['currentScrollTop']
      
      # Add random offset
      random_offset = random.randint(random_offset_range[0], random_offset_range[1])
      target_scroll = max_scroll + random_offset
      target_scroll = max(0, min(target_scroll, max_scroll))
      
      self.logger.info(f"Scrolling to bottom with offset: {random_offset}px")
      
      # Smooth scroll to target position
      if steps > 1:
        scroll_distance = target_scroll - current_scroll
        scroll_per_step = scroll_distance / steps
        
        for step in range(steps):
          intermediate_position = current_scroll + (scroll_per_step * (step + 1))
          page.evaluate(f"window.scrollTo(0, {intermediate_position})")
          page.wait_for_timeout(delay_per_step)
      else:
        # Single scroll to target
        page.evaluate(f"window.scrollTo(0, {target_scroll})")
    
      final_scroll = page.evaluate("() => window.pageYOffset")
      self.logger.info(f"Scroll complete. Final position: {final_scroll}px")
      
    except Exception as e:
        self.logger.error(f"Error during scrolling: {e}", exc_info=True)


  def mimic_mouse_movement(self, 
                           start_x=10, 
                           start_y=10, 
                           end_x=None, 
                           end_y=None, 
                           random_offset_range=100,
                           steps=10, 
                           delay_per_step=50,
                           page=None):
    """
    Mimics mouse movement to a specific element or coordinates.
    If target_element is provided, moves to its center.
    Otherwise, moves from (start_x, start_y) to (end_x, end_y).
    """
    if not page:
      self.logger.warning("No page object was passed to mimic_mouse_movement()")
      return

    # Wait for page to be ready
    try:
      page.wait_for_load_state('domcontentloaded', timeout=5000)
    except:
      self.logger.warning("Page did not load properly")
    
    # Get viewport size
    viewport_size = page.viewport_size
    if not viewport_size:
      self.logger.warning("Could not get viewport size")
      return
    
    # Set default end coordinates to center of viewport if not provided
    if end_x is None:
      end_x = viewport_size['width'] // 2
    if end_y is None:
      end_y = viewport_size['height'] // 2

    # Add random offsets
    target_x = end_x + random.randint(-random_offset_range, random_offset_range)
    target_y = end_y + random.randint(-random_offset_range, random_offset_range)

    # Ensure target coordinates are within viewport
    target_x = max(0, min(target_x, viewport_size['width'] - 1))
    target_y = max(0, min(target_y, viewport_size['height'] - 1))
    
    # Move to start position
    page.mouse.move(start_x, start_y)
    page.wait_for_timeout(delay_per_step)

    # Interpolate movement
    for i in range(1, steps + 1):
      current_x = start_x + (target_x - start_x) * i / steps
      current_y = start_y + (target_y - start_y) * i / steps
      page.mouse.move(current_x, current_y)
      page.wait_for_timeout(delay_per_step)
    
    self.logger.info(f"Mouse movement mimicked to ({target_x:.0f}, {target_y:.0f})")


  # Add this method to your AgentQLPlaywrightScraper class
  def mimic_human_actions(self, page_obj):
    """
    Callback function for agentql.paginate to perform human-like actions
    on each new page that loads during pagination.
    """
    self.logger.info(f"Performing human-like actions...")
    
    # mimic some mouse movement
    self.mimic_mouse_movement(start_x=random.randint(10, 50), 
                              start_y=random.randint(10, 50), 
                              random_offset_range=150,
                              page=page_obj) # Move from top-left towards body center
    
    # Scroll down the initial page to reveal more content or mimic user behavior
    # Choose between fixed amount or iterative to bottom
    self.scroll_page_down(steps=8, 
                          delay_per_step=70,
                          page=page_obj) # For a fixed, smooth scroll

    # You can add more actions here, e.g., waiting for specific elements
    page_obj.wait_for_timeout(500) # Small additional delay
