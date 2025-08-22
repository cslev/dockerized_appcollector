from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

import os
import sys
from typing import Optional

current_dir = os.path.abspath(os.path.dirname(__file__))
src_dir= os.path.abspath(os.path.join(current_dir, '..'))
# set sys_path to also look for libs elsewhere
sys.path.append(src_dir)
from libs.logger import CustomLogger

from database.models import Base, GitHubRepository

# Fetch from environment
POSTGRES_USER = os.getenv("POSTGRES_USER", "appcollector_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "eg2ooHooQu")
POSTGRES_DB = os.getenv("POSTGRES_DB", "appcollector")
POSTGRES_CONTAINER = os.getenv("POSTGRES_CONTAINER", "172.19.1.10")
POSTGRES_PORT=os.getenv("POSTGRES_PORT", 5432)

# Replace with your actual database URL
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_CONTAINER}:{POSTGRES_PORT}/{POSTGRES_DB}"

logger = CustomLogger("INITIALIZE_DB")

def create_db(force_recreate:bool = False) -> tuple[bool, Optional[list | str]]:
  """
  This function is to (re)create a database!
  """
  engine = create_engine(DATABASE_URL)
  Session = sessionmaker(bind=engine) # Define Session here for use in this function
  session = Session() # Create a session for this function
  try:
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    if existing_tables:
      if force_recreate:
        # we need to check if there are any views created, because we need to delete them too
        try:
          # This query gets all views in the current database, across all accessible schemas
          views_query = text("""
              SELECT schemaname, viewname
              FROM pg_views
              WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
          """)
          views_to_drop = session.execute(views_query).fetchall()
          if views_to_drop:
            logger.info(f"Found {len(views_to_drop)} view(s) to drop.")
            for schema, view_name in views_to_drop:
                full_view_name = f'"{schema}"."{view_name}"' # Quote names to handle special characters
                logger.info(f"Dropping view: {full_view_name} CASCADE;")
                session.execute(text(f"DROP VIEW {full_view_name} CASCADE;"))
            session.commit() # Commit all view drops
            logger.info("Successfully dropped all identified views.")
          else:
            logger.info("No user-defined views found to drop.")
        except Exception as e:
          logger.error(f"Error dropping views: {e}", exc_info=True)
          session.rollback() # Rollback if view drop failed
          # If view dropping fails, table dropping will likely also fail.
          # You might want to return False here, or let the next drop_all catch it.
          return (False, str(e))
        
        logger.info("Dropping all existing tables...")
        Base.metadata.drop_all(engine)
        logger.info("Creating all tables from scratch...")
        Base.metadata.create_all(engine)
        

        return (True, existing_tables)
      else:
        logger.warning("Database initialization was halted - database exists with the following tables:")
        logger.warning(existing_tables)
        return (False, existing_tables)
    else:
      logger.info("No existing tables found. Creating all tables...")
      Base.metadata.create_all(engine)
      
      return (True, None)
  except Exception as e:
    logger.error(f"❌  There was an error during initializing the database: {e}", exc_info=True)
    session.rollback() # Ensure rollback on error
    return (False, str(e))
  finally:
    session.close() # Always close the session
  
# Example usage:
if __name__ == "__main__":
  logger = CustomLogger("INIT_DB")
  logger.debug("Main function is called")
  force_recreate=False
  if force_recreate:
    logger.info("✅  Database is forced to be initialized from scratch.")
  
  db, existing_tables = create_db(force_recreate=force_recreate)
  if db:
    logger.info("✅  Database initialized from scratch. No tables existed before.")
  else:
    if isinstance(existing_tables, list):
      logger.warning("⚠️  Database initizalization was halted - database exists with the following tables ")
      logger.warning(existing_tables)
    if isinstance(existing_tables, str):
      logger.error(f"❌  There was an error during initializing the database\n{existing_tables}")