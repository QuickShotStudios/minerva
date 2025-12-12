"""Website discovery module - sitemap parsing and link crawling."""

import asyncio
import logging
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional, Set
from urllib.parse import urljoin, urlparse

from playwright.async_api import Browser, Page, async_playwright

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryConfig:
    """Configuration for website discovery."""

    domain_locked: bool = True
    include_subdomains: bool = False
    max_depth: Optional[int] = None
    max_pages: Optional[int] = None
    exclude_patterns: List[str] = field(default_factory=list)


class WebsiteDiscovery:
    """Discover pages on a website via sitemap or crawling."""

    def __init__(self, config: Optional[DiscoveryConfig] = None):
        """Initialize website discovery with configuration."""
        self.config = config or DiscoveryConfig()
        self.visited: Set[str] = set()

    async def discover_pages(self, start_url: str, browser: Browser) -> List[str]:
        """Main discovery method: try sitemap first, fall back to crawler.

        Args:
            start_url: Starting URL to discover pages from
            browser: Playwright browser instance to use

        Returns:
            List of URLs to scrape
        """
        logger.info(f"Discovering pages from {start_url}")

        # Normalize starting URL
        start_url = self._normalize_url(start_url)

        # Try sitemap first
        sitemap_urls = await self._try_sitemap(start_url, browser)
        if sitemap_urls:
            logger.info(f"Found {len(sitemap_urls)} URLs in sitemap")
            filtered = self._filter_by_scope(sitemap_urls, start_url)
            logger.info(f"After filtering: {len(filtered)} URLs")
            return filtered

        # Fall back to crawler
        logger.info("No sitemap found, falling back to crawler")
        crawled_urls = await self._crawl_site(start_url, browser)
        filtered = self._filter_by_scope(crawled_urls, start_url)
        logger.info(f"Crawled {len(crawled_urls)} URLs, filtered to {len(filtered)}")
        return filtered

    async def _try_sitemap(self, base_url: str, browser: Browser) -> Optional[List[str]]:
        """Try to fetch and parse sitemap.xml.

        Args:
            base_url: Base URL of the website
            browser: Playwright browser instance to use

        Returns:
            List of URLs from sitemap or None if not found
        """
        # Common sitemap locations
        sitemap_urls = [
            urljoin(base_url, "/sitemap.xml"),
            urljoin(base_url, "/sitemap_index.xml"),
            urljoin(base_url, "/sitemap.xml.gz"),
            urljoin(base_url, "/sitemap-index.xml"),
        ]

        for sitemap_url in sitemap_urls:
            logger.debug(f"Checking for sitemap at {sitemap_url}")
            urls = await self._parse_sitemap(browser, sitemap_url)
            if urls:
                logger.info(f"Found sitemap at {sitemap_url}")
                return urls

        return None

    async def _parse_sitemap(self, browser: Browser, sitemap_url: str) -> Optional[List[str]]:
        """Parse a sitemap.xml file.

        Args:
            browser: Playwright browser instance
            sitemap_url: URL of the sitemap

        Returns:
            List of URLs from sitemap or None if parsing failed
        """
        try:
            page = await browser.new_page()
            response = await page.goto(sitemap_url, wait_until="domcontentloaded", timeout=10000)

            if not response or response.status != 200:
                await page.close()
                return None

            content = await page.content()
            await page.close()

            # Parse XML
            root = ET.fromstring(content)

            # Handle different sitemap namespaces
            namespaces = {
                "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
                "": "http://www.sitemaps.org/schemas/sitemap/0.9",
            }

            urls = []

            # Check if this is a sitemap index (contains other sitemaps)
            sitemap_refs = root.findall(".//sm:sitemap/sm:loc", namespaces) or root.findall(
                ".//sitemap/loc"
            )

            if sitemap_refs:
                # This is a sitemap index, fetch all referenced sitemaps
                logger.debug(f"Found sitemap index with {len(sitemap_refs)} sitemaps")
                for ref in sitemap_refs:
                    sub_sitemap_url = ref.text.strip()
                    sub_urls = await self._parse_sitemap(browser, sub_sitemap_url)
                    if sub_urls:
                        urls.extend(sub_urls)
            else:
                # This is a regular sitemap, extract URLs
                url_elements = root.findall(".//sm:url/sm:loc", namespaces) or root.findall(
                    ".//url/loc"
                )
                urls = [elem.text.strip() for elem in url_elements if elem.text]
                logger.debug(f"Found {len(urls)} URLs in sitemap")

            return urls if urls else None

        except ET.ParseError as e:
            logger.debug(f"Failed to parse sitemap XML: {e}")
            return None
        except Exception as e:
            logger.debug(f"Error fetching sitemap: {e}")
            return None

    async def _crawl_site(self, start_url: str, browser: Browser) -> List[str]:
        """Crawl site by following links (BFS).

        Args:
            start_url: Starting URL for crawling
            browser: Playwright browser instance to use

        Returns:
            List of discovered URLs
        """
        discovered_urls = []
        queue = deque([(start_url, 0)])  # (url, depth)
        self.visited.clear()

        while queue:
            # Check max_pages limit
            if self.config.max_pages and len(discovered_urls) >= self.config.max_pages:
                logger.info(f"Reached max_pages limit: {self.config.max_pages}")
                break

            current_url, depth = queue.popleft()

            # Check max_depth limit
            if self.config.max_depth and depth > self.config.max_depth:
                logger.debug(f"Skipping {current_url}: exceeds max_depth")
                continue

            # Skip if already visited
            if current_url in self.visited:
                continue

            self.visited.add(current_url)
            discovered_urls.append(current_url)

            logger.debug(f"Crawling {current_url} (depth: {depth})")

            # Extract links from page
            try:
                links = await self._extract_links(browser, current_url)

                # Add new links to queue
                for link in links:
                    if link not in self.visited:
                        queue.append((link, depth + 1))

            except Exception as e:
                logger.warning(f"Error crawling {current_url}: {e}")
                continue

        return discovered_urls

    async def _extract_links(self, browser: Browser, url: str) -> List[str]:
        """Extract all links from a page.

        Args:
            browser: Playwright browser instance
            url: URL of the page to extract links from

        Returns:
            List of absolute URLs found on the page
        """
        try:
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)

            # Extract all href attributes
            links = await page.evaluate("""
                () => {
                    const anchors = Array.from(document.querySelectorAll('a[href]'));
                    return anchors.map(a => a.href);
                }
            """)

            await page.close()

            # Convert relative URLs to absolute and normalize
            absolute_links = [self._normalize_url(link) for link in links if link]

            # Filter out non-HTTP(S) links
            http_links = [link for link in absolute_links if link.startswith(("http://", "https://"))]

            return http_links

        except Exception as e:
            logger.debug(f"Error extracting links from {url}: {e}")
            return []

    def _filter_by_scope(self, urls: List[str], base_url: str) -> List[str]:
        """Filter URLs based on scope configuration.

        Args:
            urls: List of URLs to filter
            base_url: Base URL for determining scope

        Returns:
            Filtered list of URLs
        """
        base_domain = urlparse(base_url).netloc
        filtered = []

        for url in urls:
            parsed = urlparse(url)

            # Domain-locked filtering
            if self.config.domain_locked:
                if self.config.include_subdomains:
                    # Allow subdomains
                    if not parsed.netloc.endswith(base_domain.split(".", 1)[-1]):
                        continue
                else:
                    # Exact domain match only
                    if parsed.netloc != base_domain:
                        continue

            # Exclude patterns
            excluded = False
            for pattern in self.config.exclude_patterns:
                if pattern in url:
                    excluded = True
                    break

            if excluded:
                continue

            filtered.append(url)

            # Check max_pages limit
            if self.config.max_pages and len(filtered) >= self.config.max_pages:
                break

        return filtered

    def _normalize_url(self, url: str) -> str:
        """Normalize URL (remove fragments, trailing slashes, etc.).

        Args:
            url: URL to normalize

        Returns:
            Normalized URL
        """
        parsed = urlparse(url)

        # Remove fragment
        normalized = parsed._replace(fragment="").geturl()

        # Remove trailing slash (except for root)
        if normalized.endswith("/") and parsed.path not in ("", "/"):
            normalized = normalized.rstrip("/")

        return normalized
