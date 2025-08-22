from datetime import datetime
import re
import os
import json
import dateparser #this guy can convert relative timestamps (e.g., 2 days ago) to datetime
from typing import Optional

def get_current_time():
  current_local_time_naive = datetime.now()
  return current_local_time_naive

def get_timestamp():
  """
  Get the current timestamp as a formatted string.

  Returns:
      str: Current date and time in 'YYYYMMDD_HHMM' format.
            Example: '20250507_0952'
  """
  now = datetime.now()
  formatted = now.strftime("%Y%m%d_%H%M")
  return formatted

def convert_relative_date(rel_date:str)-> Optional[datetime]:
  """
  This function converts relative timestamps, like "2 days ago" into actual datetime objects
  
  Args:
    rel_date (str): the relative timestamp as string

  Returns
    datetime or None: depending on the success of the conversion
  """
  if(isinstance(rel_date,str)):
    ### Googletrans lib requires too old httpx library that conflicts with langchain!!
    #check if input is chinese
    # if(contains_chinese(text=rel_date)):
    #   result = translator.translate(rel_date, src='zh-cn', dest='en')
    #   rel_date = result.text
    try:
      date = dateparser.parse(rel_date)
    except Exception as e:
      date = None
  else:
    date = None
  
  return date