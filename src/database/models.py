"""
Database models for the GitHub repository collector.

This module contains SQLAlchemy models for storing collected GitHub repository data.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func


Base = declarative_base()


class GitHubRepository(Base):
  """
  Model for storing GitHub repository information collected during crawling.
  
  This table stores comprehensive information about GitHub repositories that
  contain docker-compose files or other containerization configurations.
  """
  
  __tablename__ = 'github_repositories'
  
  # Primary key
  id = Column(Integer, primary_key=True, autoincrement=True, comment="Unique identifier for the repository record")
  
  # Repository identification
  name = Column(String(255), nullable=False, comment="Repository name (e.g., 'blockscout/blockscout')")
  url = Column(String(500), nullable=False, unique=True, comment="Full GitHub repository URL")
  
  # Repository metadata
  about = Column(Text, nullable=True, comment="Repository description/about text")
  created_at = Column(DateTime, nullable=True, comment="When the repository was created on GitHub")
  last_commit = Column(DateTime, nullable=True, comment="Timestamp of the last commit to the repository")
  
  # Repository statistics
  num_stars = Column(Integer, default=0, nullable=False, comment="Number of stars the repository has")
  num_issues = Column(Integer, default=0, nullable=False, comment="Number of open issues")
  
  # Docker/Container related information
  num_containers = Column(Integer, default=0, nullable=False, comment="Number of containers defined in docker-compose files")
  docker_images_used = Column(JSON, nullable=True, comment="JSON array of Docker images used in the repository")
  
  # Repository quality indicators
  has_readme = Column(Boolean, default=False, nullable=False, comment="Whether the repository has a README file")
  useful_traffic = Column(Boolean, default=False, nullable=False, comment="Whether the repository shows signs of useful/active traffic")
  
  # Network/Traffic metrics
  num_packets = Column(Integer, default=0, nullable=False, comment="Number of network packets or traffic metrics")
  
  # Audit fields
  crawled_at = Column(DateTime, default=func.now(), nullable=False, comment="When this record was crawled/created")
  updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, comment="When this record was last updated")
  
  def __repr__(self) -> str:
      """String representation of the GitHubRepository object."""
      return f"<GitHubRepository(name='{self.name}', stars={self.num_stars}, containers={self.num_containers})>"
  
  def __str__(self) -> str:
      """Human-readable string representation."""
      return f"{self.name} ({self.num_stars} stars, {self.num_containers} containers)"
  