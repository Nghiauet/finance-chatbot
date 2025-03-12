"""
Utility commands for database migrations.
This file provides a programmatic way to run migrations from within the application.
"""

import logging
import os
import sys
from typing import Optional, List

from alembic import command
from alembic.config import Config
from pathlib import Path

logger = logging.getLogger(__name__)


def get_alembic_config() -> Config:
    """Get Alembic configuration."""
    # Locate alembic.ini relative to this file
    script_location = Path(__file__).parent
    alembic_ini_path = Path(__file__).parents[4] / "alembic.ini"
    
    if not alembic_ini_path.exists():
        raise FileNotFoundError(f"Alembic config file not found at {alembic_ini_path}")
    
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("script_location", str(script_location))
    
    # Override the sqlalchemy.url from environment variables if available
    from src.backend.core.config import settings
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    
    return alembic_cfg


def upgrade(revision: str = "head") -> None:
    """Upgrade database to the specified revision."""
    config = get_alembic_config()
    logger.info(f"Upgrading database to revision {revision}")
    try:
        command.upgrade(config, revision)
        logger.info("Database upgrade successful")
    except Exception as e:
        logger.error(f"Database upgrade failed: {e}")
        raise


def downgrade(revision: str) -> None:
    """Downgrade database to the specified revision."""
    config = get_alembic_config()
    logger.info(f"Downgrading database to revision {revision}")
    try:
        command.downgrade(config, revision)
        logger.info("Database downgrade successful")
    except Exception as e:
        logger.error(f"Database downgrade failed: {e}")
        raise


def revision(message: str, autogenerate: bool = True) -> None:
    """Create a new revision."""
    config = get_alembic_config()
    logger.info(f"Creating new revision: {message}")
    try:
        if autogenerate:
            command.revision(config, message=message, autogenerate=True)
        else:
            command.revision(config, message=message)
        logger.info("Revision created successfully")
    except Exception as e:
        logger.error(f"Failed to create revision: {e}")
        raise


def current() -> None:
    """Show current revision."""
    config = get_alembic_config()
    try:
        command.current(config)
    except Exception as e:
        logger.error(f"Failed to get current revision: {e}")
        raise


def history(verbose: bool = False) -> None:
    """Show revision history."""
    config = get_alembic_config()
    try:
        command.history(config, verbose=verbose)
    except Exception as e:
        logger.error(f"Failed to get revision history: {e}")
        raise


def init_db() -> None:
    """Initialize database with all tables and initial data."""
    config = get_alembic_config()
    logger.info("Initializing database")
    try:
        # Check if we need to stamp the database first (for existing databases)
        # This would typically be done only in specific scenarios
        # command.stamp(config, "head")
        
        # Upgrade to the latest migration
        command.upgrade(config, "head")
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


if __name__ == "__main__":
    """Command line interface for database migrations."""
    if len(sys.argv) < 2:
        print("Usage: python commands.py [upgrade|downgrade|revision|current|history|init]")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "upgrade":
        revision_arg = sys.argv[2] if len(sys.argv) > 2 else "head"
        upgrade(revision_arg)
    elif action == "downgrade":
        if len(sys.argv) < 3:
            print("Downgrade requires a revision argument")
            sys.exit(1)
        downgrade(sys.argv[2])
    elif action == "revision":
        if len(sys.argv) < 3:
            print("Revision requires a message argument")
            sys.exit(1)
        autogen = True
        if len(sys.argv) > 3 and sys.argv[3].lower() == "false":
            autogen = False
        revision(sys.argv[2], autogen)
    elif action == "current":
        current()
    elif action == "history":
        verbose = len(sys.argv) > 2 and sys.argv[2].lower() == "true"
        history(verbose)
    elif action == "init":
        init_db()
    else:
        print(f"Unknown action: {action}")
        print("Usage: python commands.py [upgrade|downgrade|revision|current|history|init]")
        sys.exit(1)