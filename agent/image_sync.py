"""Image sync module — downloads lock screen images from server."""

import os
import requests
import logging

logger = logging.getLogger("agent.image_sync")


class ImageSync:
    """Handles downloading and caching lock screen images from the server."""

    def __init__(self, server_url: str, cache_dir: str, verify_ssl: bool = True):
        self.server_url = server_url.rstrip("/")
        self.cache_dir = cache_dir
        self.verify_ssl = verify_ssl
        os.makedirs(cache_dir, exist_ok=True)

    def download_image(self, image_url: str) -> str:
        """Download an image from the server and cache locally.

        Args:
            image_url: Relative URL path like /api/images/file/xxx.png

        Returns:
            Local file path of the cached image
        """
        full_url = f"{self.server_url}{image_url}"
        file_name = os.path.basename(image_url)
        local_path = os.path.join(self.cache_dir, file_name)

        try:
            resp = requests.get(full_url, timeout=30, stream=True, verify=self.verify_ssl)
            resp.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"图片下载成功: {file_name}")
            return local_path
        except Exception as e:
            logger.error(f"图片下载失败: {e}")
            return ""

    def get_latest_image(self) -> str:
        """Return the path of the most recently cached image."""
        if not os.path.exists(self.cache_dir):
            return ""
        files = [
            os.path.join(self.cache_dir, f)
            for f in os.listdir(self.cache_dir)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp'))
        ]
        if not files:
            return ""
        return max(files, key=os.path.getmtime)
