"""
Archive Handler - Integration with archive.org Wayback Machine
Ported from archive-org.ts
"""

import requests
from typing import Dict, List, Optional
from datetime import datetime
import time


class ArchiveHandler:
    """Handle archive.org Wayback Machine operations"""

    def __init__(self):
        self.base_url = "https://web.archive.org"

    def archive_url(self, url: str, timeout: int = 30) -> Dict:
        """
        Archive a single URL to the Wayback Machine

        Args:
            url: URL to archive
            timeout: Request timeout in seconds

        Returns:
            Dictionary with archive information
        """
        try:
            # Save to Wayback Machine
            save_url = f"{self.base_url}/save/{url}"

            response = requests.get(
                save_url,
                timeout=timeout,
                allow_redirects=True
            )

            # Try to get archived URL from response
            archive_url = None

            # Check Content-Location header
            if 'content-location' in response.headers:
                archive_url = f"{self.base_url}{response.headers['content-location']}"
            else:
                # Fallback: construct URL manually with current timestamp
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                archive_url = f"{self.base_url}/web/{timestamp}/{url}"

            return {
                'original_url': url,
                'archive_url': archive_url,
                'archived_at': datetime.now().isoformat(),
                'success': True
            }

        except Exception as e:
            print(f"Failed to archive URL {url}: {e}")
            return {
                'original_url': url,
                'archive_url': None,
                'archived_at': datetime.now().isoformat(),
                'success': False,
                'error': str(e)
            }

    def archive_multiple_urls(
        self,
        urls: List[str],
        on_progress: Optional[callable] = None,
        delay: int = 1
    ) -> List[Dict]:
        """
        Archive multiple URLs with progress tracking

        Args:
            urls: List of URLs to archive
            on_progress: Callback function(current, total, url)
            delay: Delay between requests in seconds (to avoid rate limiting)

        Returns:
            List of archive results
        """
        results = []

        for idx, url in enumerate(urls):
            # Progress callback
            if on_progress:
                on_progress(idx + 1, len(urls), url)

            # Archive the URL
            result = self.archive_url(url)
            results.append(result)

            # Delay between requests (be nice to archive.org)
            if idx < len(urls) - 1:
                time.sleep(delay)

        return results

    def check_existing_archive(self, url: str, timeout: int = 10) -> Optional[str]:
        """
        Check if URL has already been archived

        Args:
            url: URL to check
            timeout: Request timeout in seconds

        Returns:
            Most recent archive URL if exists, None otherwise
        """
        try:
            availability_url = f"{self.base_url}/wayback/available"
            params = {'url': url}

            response = requests.get(
                availability_url,
                params=params,
                timeout=timeout
            )

            data = response.json()

            if (data.get('archived_snapshots', {})
                    .get('closest', {})
                    .get('available')):
                return data['archived_snapshots']['closest']['url']

            return None

        except Exception as e:
            print(f"Error checking existing archive for {url}: {e}")
            return None

    def archive_url_smart(self, url: str) -> Dict:
        """
        Archive URL with fallback to existing archive

        First checks if URL is already archived, if so returns that.
        Otherwise archives it fresh.

        Args:
            url: URL to archive

        Returns:
            Archive result dictionary
        """
        # Check if already archived
        existing = self.check_existing_archive(url)

        if existing:
            return {
                'original_url': url,
                'archive_url': existing,
                'archived_at': datetime.now().isoformat(),
                'success': True,
                'used_existing': True
            }

        # Archive fresh
        result = self.archive_url(url)
        result['used_existing'] = False
        return result

    def get_statistics(self, results: List[Dict]) -> Dict:
        """
        Get statistics about archived URLs

        Args:
            results: List of archive results

        Returns:
            Statistics dictionary
        """
        total = len(results)
        successful = sum(1 for r in results if r.get('success'))
        failed = total - successful
        success_rate = (successful / total * 100) if total > 0 else 0

        return {
            'total': total,
            'successful': successful,
            'failed': failed,
            'success_rate': success_rate
        }
