"""
Example of how to integrate the database with your GitHub repository collector.

This shows how to save collected repository data to the PostgreSQL database.
"""

import os
import sys
from datetime import datetime
from typing import List, Dict

# Add the src directory to the path so we can import our modules
current_dir = os.path.abspath(os.path.dirname(__file__))
src_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(src_dir)

from database import init_database, save_repository, get_all_repositories, GitHubRepository
from libs.logger import CustomLogger

logger = CustomLogger("DatabaseExample")


def setup_database():
    """Initialize the database and create tables."""
    try:
        # Initialize database (will use environment variables or defaults)
        db_manager = init_database()
        
        # Create tables if they don't exist
        db_manager.create_tables()
        
        logger.info("Database setup completed successfully")
        return db_manager
    except Exception as e:
        logger.error(f"Error setting up database: {e}")
        raise


def save_github_repo_data(repo_data: Dict) -> GitHubRepository:
    """
    Save GitHub repository data to the database.
    
    Args:
        repo_data: Dictionary containing repository information
        
    Returns:
        GitHubRepository: The saved repository object
    """
    try:
        # Example of how to transform your scraped data to fit the model
        processed_data = {
            'name': repo_data.get('name', ''),
            'url': repo_data.get('project_url', ''),
            'about': repo_data.get('description', ''),
            'created_at': parse_date(repo_data.get('created_at')),
            'last_commit': parse_date(repo_data.get('last_commit')),
            'num_stars': int(repo_data.get('stars', 0)),
            'num_issues': int(repo_data.get('issues', 0)),
            'num_containers': int(repo_data.get('containers', 0)),
            'docker_images_used': repo_data.get('docker_images', []),
            'has_readme': bool(repo_data.get('has_readme', False)),
            'useful_traffic': bool(repo_data.get('useful_traffic', False)),
            'num_packets': int(repo_data.get('packets', 0))
        }
        
        # Save to database
        repository = save_repository(processed_data)
        logger.info(f"Saved repository: {repository.name}")
        
        return repository
        
    except Exception as e:
        logger.error(f"Error saving repository data: {e}")
        raise


def parse_date(date_string):
    """Parse a date string into a datetime object."""
    if not date_string:
        return None
    
    try:
        # Add more date formats as needed based on your data
        if isinstance(date_string, str):
            return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        elif isinstance(date_string, datetime):
            return date_string
        else:
            return None
    except (ValueError, AttributeError):
        logger.warning(f"Could not parse date: {date_string}")
        return None


def example_integration_with_appcollector():
    """Example of how to integrate with your existing appcollector.py"""
    
    # Setup database
    setup_database()
    
    # Example of collected data (this would come from your scraper)
    scraped_repositories = [
        {
            'name': 'blockscout/blockscout',
            'project_url': 'https://github.com/blockscout/blockscout',
            'description': 'Blockchain explorer for Ethereum based network',
            'stars': 2800,
            'issues': 45,
            'containers': 5,
            'docker_images': ['postgres:13', 'redis:6', 'nginx:alpine'],
            'has_readme': True,
            'useful_traffic': True,
            'packets': 1500
        },
        {
            'name': 'docker/compose',
            'project_url': 'https://github.com/docker/compose',
            'description': 'Define and run multi-container applications with Docker',
            'stars': 31000,
            'issues': 120,
            'containers': 3,
            'docker_images': ['python:3.9', 'alpine:latest'],
            'has_readme': True,
            'useful_traffic': True,
            'packets': 2000
        }
    ]
    
    # Save each repository to the database
    saved_repos = []
    for repo_data in scraped_repositories:
        saved_repo = save_github_repo_data(repo_data)
        saved_repos.append(saved_repo)
    
    # Query and display saved repositories
    all_repos = get_all_repositories()
    logger.info(f"\nTotal repositories in database: {len(all_repos)}")
    
    for repo in all_repos:
        logger.info(f"- {repo.name}: {repo.num_stars} stars, {repo.num_containers} containers")


def print_database_schema():
    """Print the database schema for reference."""
    from database.models import get_table_info
    
    table_info = get_table_info()
    
    print("\n" + "="*60)
    print("DATABASE SCHEMA")
    print("="*60)
    print(f"Table: {table_info['table_name']}")
    print("-" * 60)
    
    for col in table_info['columns']:
        pk_marker = " (PRIMARY KEY)" if col['primary_key'] else ""
        nullable_marker = " NOT NULL" if not col['nullable'] else ""
        
        print(f"{col['name']:<20} {col['type']:<20} {nullable_marker:<10} {pk_marker}")
        if col['comment']:
            print(f"    # {col['comment']}")
        print()


if __name__ == "__main__":
    # Print the database schema
    print_database_schema()
    
    # Run the example integration
    example_integration_with_appcollector()
