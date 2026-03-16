"""Immich API client for album management."""

import requests
from typing import Any, Dict, List, Optional


class ImmichAPI:
    """Client for interacting with Immich server API."""

    def __init__(self, api_url: str, api_key: str, timeout: int = 30):
        """
        Initialize Immich API client.

        Args:
            api_url: Base URL for Immich API (e.g., http://localhost:2283/api/)
            api_key: API key for authentication
            timeout: Request timeout in seconds
        """
        self.api_url = api_url.rstrip("/")
        self.headers = {"x-api-key": api_key}
        self.timeout = timeout

    def _request(
        self,
        method: str,
        endpoint: str,
        json: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> requests.Response:
        """Make an API request."""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        response = requests.request(
            method=method,
            url=url,
            headers=self.headers,
            json=json,
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response

    def get_server_version(self) -> Dict[str, Any]:
        """Get Immich server version."""
        return self._request("GET", "/server/version").json()

    def get_albums(self) -> List[Dict[str, Any]]:
        """Get all albums."""
        return self._request("GET", "/albums").json()

    def get_album(self, album_id: str) -> Dict[str, Any]:
        """Get a specific album by ID."""
        return self._request("GET", f"/albums/{album_id}").json()

    def create_album(self, name: str, description: str = "") -> Dict[str, Any]:
        """Create a new album."""
        return self._request(
            "POST",
            "/albums",
            json={"albumName": name, "description": description},
        ).json()

    def delete_album(self, album_id: str) -> bool:
        """
        Delete an album by ID.

        Args:
            album_id: The album ID to delete

        Returns:
            True if deletion was successful
        """
        response = self._request("DELETE", f"/albums/{album_id}")
        return response.status_code in [200, 204]

    def delete_albums(self, album_ids: List[str]) -> Dict[str, List[str]]:
        """
        Delete multiple albums.

        Args:
            album_ids: List of album IDs to delete

        Returns:
            Dict with 'success' and 'failed' lists of album IDs
        """
        results = {"success": [], "failed": []}
        for album_id in album_ids:
            try:
                if self.delete_album(album_id):
                    results["success"].append(album_id)
                else:
                    results["failed"].append(album_id)
            except Exception:
                results["failed"].append(album_id)
        return results

    def get_albums_by_names(self, names: List[str]) -> List[Dict[str, Any]]:
        """
        Get albums that match the given names.

        Args:
            names: List of album names to match

        Returns:
            List of matching albums
        """
        all_albums = self.get_albums()
        name_set = set(names)
        return [a for a in all_albums if a["albumName"] in name_set]

    def get_orphan_albums(self, valid_names: List[str]) -> List[Dict[str, Any]]:
        """
        Get albums that don't match any of the valid names.

        Args:
            valid_names: List of valid album names based on folder structure

        Returns:
            List of orphan albums
        """
        all_albums = self.get_albums()
        valid_set = set(valid_names)
        return [a for a in all_albums if a["albumName"] not in valid_set]

    def get_all_assets(
        self, page_size: int = 1000, with_exif: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all assets from Immich using pagination.

        Args:
            page_size: Number of assets to fetch per page
            with_exif: Include EXIF data (needed for file size)

        Returns:
            List of all assets
        """
        all_assets = []
        page = 1

        while True:
            request_body = {"size": page_size, "page": str(page)}
            if with_exif:
                request_body["withExif"] = True

            response = self._request(
                "POST",
                "/search/metadata",
                json=request_body,
            )
            data = response.json()
            assets = data.get("assets", {}).get("items", [])

            if not assets:
                break

            all_assets.extend(assets)
            page += 1

            # Safety limit
            if page > 1000:
                break

        return all_assets

    def delete_asset(self, asset_id: str, force: bool = False) -> bool:
        """
        Delete an asset (moves to trash unless force=True).

        Args:
            asset_id: The asset ID to delete
            force: If True, permanently delete. If False, move to trash.

        Returns:
            True if deletion was successful
        """
        response = self._request(
            "DELETE",
            "/assets",
            json={"ids": [asset_id], "force": force},
        )
        return response.status_code in [200, 204]

    def get_trashed_assets(
        self, page_size: int = 1000, include_offline: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all trashed and/or offline assets from Immich.

        Note: The Immich search API isTrashed filter doesn't work reliably.
        Use trashedAfter parameter instead to find trashed items.

        Args:
            page_size: Number of assets to fetch per page
            include_offline: Also include offline assets (external library files not on disk)

        Returns:
            List of trashed/offline assets
        """
        all_assets = []
        seen_ids = set()

        # Use trashedAfter to get trashed items (isTrashed filter unreliable)
        page = 1
        while True:
            response = self._request(
                "POST",
                "/search/metadata",
                json={
                    "size": page_size,
                    "page": str(page),
                    "trashedAfter": "1970-01-01",  # Get all trashed items
                    "withExif": True,
                },
            )
            data = response.json()
            assets = data.get("assets", {}).get("items", [])

            if not assets:
                break

            for a in assets:
                if a["id"] not in seen_ids:
                    seen_ids.add(a["id"])
                    all_assets.append(a)

            page += 1
            if page > 1000:
                break

        # Also fetch offline assets (external library files not found on disk)
        if include_offline:
            page = 1
            while True:
                response = self._request(
                    "POST",
                    "/search/metadata",
                    json={
                        "size": page_size,
                        "page": str(page),
                        "isOffline": True,
                        "withExif": True,
                    },
                )
                data = response.json()
                assets = data.get("assets", {}).get("items", [])

                if not assets:
                    break

                for a in assets:
                    if a["id"] not in seen_ids:
                        # Verify it's actually offline
                        if a.get("isOffline", False) == True:
                            seen_ids.add(a["id"])
                            all_assets.append(a)

                page += 1
                if page > 1000:
                    break

        return all_assets

    def restore_assets(self, asset_ids: List[str]) -> bool:
        """
        Restore assets from trash.

        Args:
            asset_ids: List of asset IDs to restore

        Returns:
            True if successful
        """
        if not asset_ids:
            return True
        response = self._request(
            "POST",
            "/trash/restore/assets",
            json={"ids": asset_ids},
        )
        return response.status_code in [200, 204]

    def empty_trash(self) -> bool:
        """
        Empty all items from trash.

        Returns:
            True if successful
        """
        response = self._request("POST", "/trash/empty")
        return response.status_code in [200, 204]

    def delete_assets(
        self, asset_ids: List[str], force: bool = False
    ) -> Dict[str, List[str]]:
        """
        Delete multiple assets.

        Args:
            asset_ids: List of asset IDs to delete
            force: If True, permanently delete. If False, move to trash.

        Returns:
            Dict with 'success' and 'failed' lists of asset IDs
        """
        if not asset_ids:
            return {"success": [], "failed": []}

        # Immich supports bulk delete
        try:
            response = self._request(
                "DELETE",
                "/assets",
                json={"ids": asset_ids, "force": force},
            )
            if response.status_code in [200, 204]:
                return {"success": asset_ids, "failed": []}
            else:
                return {"success": [], "failed": asset_ids}
        except Exception:
            return {"success": [], "failed": asset_ids}
