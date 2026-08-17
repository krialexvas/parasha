"""
News Collector Module
Collects news from websites and Telegram channels
"""

import logging
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urljoin
import re

logger = logging.getLogger(__name__)


class NewsItem:
    """Represents a single news item"""
    
    def __init__(self, title: str, content: str, source: str, url: str, 
                 published_date: Optional[datetime] = None, image_url: Optional[str] = None):
        self.title = title
        self.content = content
        self.source = source
        self.url = url
        self.published_date = published_date or datetime.now()
        self.image_url = image_url
    
    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "url": self.url,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "image_url": self.image_url
        }
    
    def __str__(self) -> str:
        return f"{self.title} ({self.source})"


class WebsiteScraper:
    """Scrapes news from websites"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    async def fetch_page(self, url: str) -> Optional[str]:
        """Fetch HTML content from URL"""
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        return await response.text(encoding='utf-8')
                    else:
                        logger.error(f"Failed to fetch {url}: Status {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    async def scrape_dzen(self, url: str, count: int, filter_keyword: Optional[str] = None) -> List[NewsItem]:
        """Scrape news from Dzen.ru"""
        news_items = []
        html = await self.fetch_page(url)
        
        if not html:
            return news_items
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Dzen structure - adjust selectors based on actual page structure
        articles = soup.find_all('article', limit=count * 3)  # Get more to filter
        
        for article in articles[:count * 2]:
            try:
                title_elem = article.find(['h2', 'h3'], class_=re.compile(r'title|heading', re.I))
                if not title_elem:
                    title_elem = article.find(['h2', 'h3'])
                
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # Apply filter if specified
                if filter_keyword and filter_keyword not in title:
                    continue
                
                link_elem = article.find('a', href=True)
                link = link_elem['href'] if link_elem else url
                
                if not link.startswith('http'):
                    link = urljoin(url, link)
                
                # Get content/description
                content_elem = article.find(['p', 'div'], class_=re.compile(r'desc|content|text', re.I))
                content = content_elem.get_text(strip=True) if content_elem else title
                
                # Get image if available
                img_elem = article.find('img')
                image_url = img_elem.get('src') if img_elem else None
                
                news_items.append(NewsItem(
                    title=title,
                    content=content,
                    source="Dzen",
                    url=link,
                    image_url=image_url
                ))
                
                if len(news_items) >= count:
                    break
                    
            except Exception as e:
                logger.error(f"Error parsing article: {e}")
                continue
        
        return news_items
    
    async def scrape_polymerbranch(self, url: str, count: int) -> List[NewsItem]:
        """Scrape news from polymerbranch.com"""
        news_items = []
        html = await self.fetch_page(url)
        
        if not html:
            return news_items
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find news items - adjust selectors based on actual structure
        articles = soup.find_all('article', limit=count)
        if not articles:
            articles = soup.find_all('div', class_=re.compile(r'news|post|article', re.I), limit=count)
        
        for article in articles:
            try:
                title_elem = article.find(['h2', 'h3', 'h4'], class_=re.compile(r'title|heading', re.I))
                if not title_elem:
                    title_elem = article.find(['h2', 'h3', 'h4'])
                
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                link_elem = article.find('a', href=True)
                link = link_elem['href'] if link_elem else url
                
                if not link.startswith('http'):
                    link = urljoin(url, link)
                
                content_elem = article.find(['p', 'div'], class_=re.compile(r'desc|excerpt|summary', re.I))
                content = content_elem.get_text(strip=True) if content_elem else title
                
                img_elem = article.find('img')
                image_url = img_elem.get('src') if img_elem else None
                
                news_items.append(NewsItem(
                    title=title,
                    content=content,
                    source="PolymerBranch",
                    url=link,
                    image_url=image_url
                ))
                
            except Exception as e:
                logger.error(f"Error parsing article: {e}")
                continue
        
        return news_items[:count]
    
    async def scrape_plastinfo(self, url: str, count: int) -> List[NewsItem]:
        """Scrape news from plastinfo.ru"""
        news_items = []
        html = await self.fetch_page(url)
        
        if not html:
            return news_items
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Plastinfo structure
        articles = soup.find_all('div', class_=re.compile(r'news|item', re.I), limit=count * 2)
        
        for article in articles:
            try:
                title_elem = article.find(['a', 'h3', 'h4'], class_=re.compile(r'title|name', re.I))
                if not title_elem:
                    title_elem = article.find('a', href=True)
                
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                link = title_elem.get('href', '')
                
                if not link.startswith('http'):
                    link = urljoin(url, link)
                
                content_elem = article.find(['p', 'div'], class_=re.compile(r'desc|text|announce', re.I))
                content = content_elem.get_text(strip=True) if content_elem else title
                
                date_elem = article.find(class_=re.compile(r'date|time', re.I))
                published_date = None
                if date_elem:
                    date_str = date_elem.get_text(strip=True)
                    # Try to parse date
                    try:
                        published_date = datetime.strptime(date_str, '%d.%m.%Y')
                    except:
                        pass
                
                news_items.append(NewsItem(
                    title=title,
                    content=content,
                    source="PlastInfo",
                    url=link,
                    published_date=published_date
                ))
                
            except Exception as e:
                logger.error(f"Error parsing article: {e}")
                continue
        
        return news_items[:count]
    
    async def scrape_generic(self, url: str, count: int) -> List[NewsItem]:
        """Generic scraper for other websites"""
        news_items = []
        html = await self.fetch_page(url)
        
        if not html:
            return news_items
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Try common patterns
        articles = soup.find_all('article', limit=count * 2)
        if not articles:
            articles = soup.find_all('div', class_=re.compile(r'news|post|article|item', re.I), limit=count * 2)
        if not articles:
            articles = soup.find_all(['li', 'div'], limit=count * 2)
        
        for article in articles:
            try:
                title_elem = article.find(['h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|heading|name', re.I))
                if not title_elem:
                    title_elem = article.find(['h2', 'h3', 'h4', 'a'])
                
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                if len(title) < 10:  # Skip very short titles
                    continue
                
                link_elem = article.find('a', href=True)
                link = link_elem['href'] if link_elem else url
                
                if not link.startswith('http'):
                    link = urljoin(url, link)
                
                content_elem = article.find(['p', 'div'], class_=re.compile(r'desc|excerpt|summary|text', re.I))
                content = content_elem.get_text(strip=True) if content_elem else title
                
                img_elem = article.find('img')
                image_url = img_elem.get('src') if img_elem else None
                
                news_items.append(NewsItem(
                    title=title,
                    content=content,
                    source="Website",
                    url=link,
                    image_url=image_url
                ))
                
            except Exception as e:
                logger.error(f"Error parsing article: {e}")
                continue
        
        return news_items[:count]
    
    async def scrape_website(self, source_name: str, config: dict) -> List[NewsItem]:
        """Scrape a website based on its configuration"""
        url = config['url']
        count = config.get('count', 1)
        filter_keyword = config.get('filter_keyword')
        
        logger.info(f"Scraping {source_name} from {url}")
        
        if 'dzen.ru' in url:
            return await self.scrape_dzen(url, count, filter_keyword)
        elif 'polymerbranch.com' in url:
            return await self.scrape_polymerbranch(url, count)
        elif 'plastinfo.ru' in url:
            return await self.scrape_plastinfo(url, count)
        else:
            return await self.scrape_generic(url, count)


class TelegramNewsCollector:
    """Collects news from Telegram channels using Telethon"""
    
    def __init__(self, api_id: int, api_hash: str, session_name: str = 'news_bot_session'):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.client = None
    
    async def connect(self):
        """Initialize Telethon client"""
        from telethon import TelegramClient
        
        self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
        await self.client.start()
        logger.info("Connected to Telegram")
    
    async def disconnect(self):
        """Disconnect from Telegram"""
        if self.client:
            await self.client.disconnect()
            logger.info("Disconnected from Telegram")
    
    async def get_channel_messages(self, username: str, count: int) -> List[NewsItem]:
        """Get recent messages from a Telegram channel"""
        news_items = []
        
        if not self.client:
            await self.connect()
        
        try:
            channel = await self.client.get_entity(username)
            
            async for message in self.client.iter_messages(channel, limit=count):
                if message.text and len(message.text) > 20:  # Skip very short messages
                    title = message.text.split('\n')[0][:100]  # First line as title
                    content = message.text
                    
                    # Get media if available
                    image_url = None
                    if message.media:
                        from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
                        if isinstance(message.media, (MessageMediaPhoto, MessageMediaDocument)):
                            # Note: Downloading and hosting images would require additional setup
                            image_url = "media_available"  # Placeholder
                    
                    news_items.append(NewsItem(
                        title=title,
                        content=content,
                        source=f"Telegram: @{username}",
                        url=f"https://t.me/{username}/{message.id}",
                        published_date=message.date,
                        image_url=image_url
                    ))
                    
                    if len(news_items) >= count:
                        break
            
            logger.info(f"Collected {len(news_items)} messages from @{username}")
            
        except Exception as e:
            logger.error(f"Error getting messages from @{username}: {e}")
        
        return news_items


class NewsCollector:
    """Main news collector class"""
    
    def __init__(self, tg_api_id: int = None, tg_api_hash: str = None):
        self.website_scraper = WebsiteScraper()
        self.tg_collector = None
        
        # Try to import from config if not provided
        if tg_api_id is None or tg_api_hash is None:
            try:
                from config import TG_API_ID, TG_API_HASH
                if TG_API_ID and TG_API_HASH and TG_API_ID != "YOUR_TG_API_ID_HERE":
                    tg_api_id = TG_API_ID
                    tg_api_hash = TG_API_HASH
            except ImportError:
                pass
        
        if tg_api_id and tg_api_hash:
            self.tg_collector = TelegramNewsCollector(tg_api_id, tg_api_hash)
    
    async def collect_all_news(self, sources_config: dict) -> List[NewsItem]:
        """Collect news from all configured sources"""
        all_news = []
        
        # Collect from websites
        websites = sources_config.get('websites', {})
        for source_name, config in websites.items():
            try:
                news = await self.website_scraper.scrape_website(source_name, config)
                all_news.extend(news)
                logger.info(f"Collected {len(news)} news from {source_name}")
            except Exception as e:
                logger.error(f"Error collecting from {source_name}: {e}")
        
        # Collect from Telegram channels
        if self.tg_collector:
            telegram_channels = sources_config.get('telegram_channels', {})
            try:
                await self.tg_collector.connect()
                
                for channel_name, config in telegram_channels.items():
                    try:
                        username = config['username']
                        count = config.get('count', 5)
                        news = await self.tg_collector.get_channel_messages(username, count)
                        all_news.extend(news)
                        logger.info(f"Collected {len(news)} news from @{username}")
                    except Exception as e:
                        logger.error(f"Error collecting from @{channel_name}: {e}")
                
                await self.tg_collector.disconnect()
            except Exception as e:
                logger.error(f"Error connecting to Telegram: {e}")
        else:
            logger.warning("Telegram API credentials not provided, skipping Telegram channels")
        
        logger.info(f"Total news collected: {len(all_news)}")
        return all_news
