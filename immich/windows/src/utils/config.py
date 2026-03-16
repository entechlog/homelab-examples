"""Configuration loader for Immich album management scripts."""

import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv


class Config:
    """Configuration management for Immich scripts."""

    def __init__(self, env_path: Optional[str] = None):
        """
        Initialize configuration from .env file.

        Args:
            env_path: Path to .env file. Defaults to project root .env
        """
        if env_path is None:
            # Default to .env in project root (parent of src/)
            env_path = Path(__file__).parent.parent.parent / ".env"

        load_dotenv(env_path)

        self.api_url = self._get_required("IMMICH_API_URL_INTERNAL")
        self.api_key = self._get_required("IMMICH_FOLDER_ALBUM_CREATOR_API_KEY")
        self.external_lib_location = self._get_required("EXTERNAL_LIB_LOCATION")
        self.album_levels = int(os.getenv("IMMICH_FOLDER_ALBUM_CREATOR_ALBUM_LEVELS", "1"))

        # Parse comma-separated root paths
        root_path_str = self._get_required("IMMICH_FOLDER_ALBUM_CREATOR_ROOT_PATH")
        self.root_paths = [p.strip() for p in root_path_str.split(",")]

    def _get_required(self, key: str) -> str:
        """Get a required environment variable."""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Missing required environment variable: {key}")
        return value

    def get_local_root_paths(self) -> List[str]:
        """
        Convert container paths to local filesystem paths.

        Container path: /photos/Siva -> Local path: F:/Photos/Siva
        When running inside container: /photos/Siva stays as /photos/Siva
        """
        local_paths = []

        # Check if running inside container (EXTERNAL_LIB_LOCATION = /photos)
        if self.external_lib_location == "/photos":
            # Running inside container, use paths as-is
            return [p.rstrip("/") for p in self.root_paths]

        for root_path in self.root_paths:
            # Replace /photos with the actual external lib location
            relative = root_path.replace("/photos/", "").replace("/photos", "")
            if relative:
                local_path = os.path.join(self.external_lib_location, relative)
            else:
                local_path = self.external_lib_location
            local_paths.append(local_path)
        return local_paths

    def get_album_separator(self) -> str:
        """Get the album level separator (default is space)."""
        return os.getenv("IMMICH_FOLDER_ALBUM_CREATOR_ALBUM_LEVEL_SEPARATOR", " ")
