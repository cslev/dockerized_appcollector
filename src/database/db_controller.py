from sqlalchemy import create_engine, inspect, text, func
from sqlalchemy.orm import sessionmaker, Session

import os
import sys
from typing import Optional, Any, Dict
from datetime import datetime

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
POSTGRES_CONTAINER = os.getenv("POSTGRES_CONTAINER", "172.18.1.24")
POSTGRES_PORT=os.getenv("POSTGRES_PORT", 5432)

# Replace with your actual database URL
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_CONTAINER}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Create engine and session factory
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

logger = CustomLogger("INITIALIZE_DB")

def get_session():
  """
  Creates and returns a new database session.
  Remember to close the session when done.
  
  Returns:
    Session: SQLAlchemy session object
  """
  return SessionLocal()

def create_db(force_recreate:bool = False) -> tuple[bool, Optional[list | str]]:
  """
  This function is to (re)create a database!
  """
  session = get_session() # Create a session for this function
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

def add_or_update_github_repository(session: Session,
                                    developer: Optional[str] = None,
                                    name: Optional[str] = None,
                                    url: Optional[str] = None,
                                    about: Optional[str] = None,
                                    created_at: Optional[datetime] = None,
                                    last_commit: Optional[datetime] = None,
                                    num_stars: int = 0,
                                    num_issues: int = 0,
                                    num_containers: int = 0,
                                    docker_images_used: Optional[Any] = None,
                                    has_readme: bool = True,
                                    useful_traffic: bool = True,
                                    num_packets: int = 0,
                                    crawled_at: Optional[datetime] = None,
                                    updated_at: Optional[datetime] = None) -> GitHubRepository:
  """
  Adds a new GitHubRepository entry to the database. If an entry with the same url exists,
  updates its details with the provided arguments.

  Args:
    session (Session): SQLAlchemy session object.
    developer (Optional[str]): GitHub username or organization that owns the repository (e.g., 'blockscout').
    name (Optional[str]): Repository name (e.g., 'blockscout').
    url (Optional[str]): Full GitHub repository URL. (Required)
    about (Optional[str]): Repository description/about text.
    created_at (Optional[datetime]): When the repository was created on GitHub.
    last_commit (Optional[datetime]): Timestamp of the last commit to the repository.
    num_stars (int): Number of stars the repository has.
    num_issues (int): Number of open issues.
    num_containers (int): Number of containers defined in docker-compose files.
    docker_images_used (Optional[Any]): JSON array of Docker images used in the repository.
    has_readme (bool): Whether the repository has a README file.
    useful_traffic (bool): Whether the repository shows signs of useful/active traffic.
    num_packets (int): Number of network packets or traffic metrics.
    crawled_at (Optional[datetime]): When this record was crawled/created.
    updated_at (Optional[datetime]): When this record was last updated.

  Returns:
    GitHubRepository: The GitHubRepository instance (added or updated)
  """
  if not url:
    raise ValueError("'url' must be provided")
  instance = session.query(GitHubRepository).filter_by(url=url).first()
  fields: Dict[str, Any] = dict(
    developer=developer,
    name=name,
    url=url,
    about=about,
    created_at=created_at,
    last_commit=last_commit,
    num_stars=num_stars,
    num_issues=num_issues,
    num_containers=num_containers,
    docker_images_used=docker_images_used,
    has_readme=has_readme,
    useful_traffic=useful_traffic,
    num_packets=num_packets,
    crawled_at=crawled_at,
    updated_at=updated_at
  )
  if instance:
    # Update existing instance
    for key, value in fields.items():
      if value is not None and hasattr(instance, key):
        setattr(instance, key, value)
    # Always update the updated_at timestamp for existing records
    setattr(instance, 'updated_at', datetime.now())
    # Don't commit here - let the caller handle it
    return instance
  else:
    # Create new instance
    filtered_fields = {k: v for k, v in fields.items() if v is not None}
    instance = GitHubRepository(**filtered_fields)
    session.add(instance)
    # Don't commit here - let the caller handle it
    return instance
  

if __name__ == "__main__":
  logger = CustomLogger("INIT_DB")
  logger.debug("Main function is called")
  force_recreate=True
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
  
  # Example usage of add_or_update_github_repository:
  session = get_session()
  try:
    repo = add_or_update_github_repository(
      session, 
      url="https://github.com/example/repo",
      developer='example',
      name="repo",
      num_stars=100
    )
    print(f"Repository added/updated: {repo}")
  finally:
    session.close()