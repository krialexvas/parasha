"""
Website news parser using BeautifulSoup and aiohttp.
Collects recent articles from configured news websites with custom parsers for each site.
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import aiohttp
from bs4 import BeautifulSoup

from config import MAX_NEWS_PER_RUN, REQUEST_TIMEOUT


class WebParser:
    """Parser for news websites with custom implementations for specific sites."""
    
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        }
    
    async def connect(self):
        """Initialize HTTP session."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            self.session = aiohttp.ClientSession(headers=self.headers, timeout=timeout)
    
    async def disconnect(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def fetch_page(self, url: str) -> Optional[str]:
        """Fetch HTML content from a URL."""
        try:
            await self.connect()
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.text(encoding='utf-8')
                elif response.status == 403:
                    print(f"Access forbidden to {url}. Try adding headers or checking robots.txt")
        except Exception as e:
            print(f"Error fetching {url}: {str(e)}")
        return None
    
    def parse_dzen_proplast(self, html: str, base_url: str) -> List[Dict]:
        """
        Parse https://dzen.ru/proplast
        Берет 1 новость в заголовке которой "1 неделю назад Сравнение цен на полимеры за"
        """
        news_items = []
        soup = BeautifulSoup(html, 'lxml')
        
        # Dzen uses specific structure - look for articles with specific date pattern
        # Find all article cards
        articles = soup.find_all(['article', 'div'], class_=lambda x: x and ('card' in x.lower() or 'post' in x.lower() or 'item' in x.lower()))
        
        if not articles:
            # Fallback: try to find any link blocks
            articles = soup.find_all('a', href=True)[:20]
        
        for article in articles:
            text_content = article.get_text(strip=True)
            
            # Look for the specific pattern: "1 неделю назад" and "Сравнение цен на полимеры за"
            if '1 неделю назад' in text_content and 'Сравнение цен на полимеры за' in text_content:
                # Extract title
                title = text_content[:300]
                
                # Get link
                link_elem = article.find('a', href=True)
                if link_elem:
                    link = urljoin(base_url, link_elem['href'])
                else:
                    link = base_url
                
                news_item = {
                    'title': title,
                    'content': text_content[:1000],
                    'date': datetime.utcnow().isoformat(),
                    'source': 'dzen.ru/proplast',
                    'source_type': 'website',
                    'link': link,
                    'media_url': None,
                    'parser_type': 'dzen_proplast'
                }
                news_items.append(news_item)
                break  # Only need 1 news item
        
        return news_items[:1]
    
    def parse_dzen_okstanok(self, html: str, base_url: str) -> List[Dict]:
        """
        Parse https://dzen.ru/okstanok
        Берет последнюю новость
        """
        news_items = []
        soup = BeautifulSoup(html, 'lxml')
        
        # Find first article/post
        articles = soup.find_all(['article', 'div'], class_=lambda x: x and ('card' in x.lower() or 'post' in x.lower() or 'item' in x.lower()))
        
        if not articles:
            articles = soup.find_all('a', href=True)[:10]
        
        if articles:
            article = articles[0]
            text_content = article.get_text(strip=True)[:500]
            
            if text_content:
                link_elem = article.find('a', href=True)
                link = urljoin(base_url, link_elem['href']) if link_elem else base_url
                
                news_item = {
                    'title': text_content.split('\n')[0][:200],
                    'content': text_content,
                    'date': datetime.utcnow().isoformat(),
                    'source': 'dzen.ru/okstanok',
                    'source_type': 'website',
                    'link': link,
                    'media_url': None,
                    'parser_type': 'dzen_okstanok'
                }
                news_items.append(news_item)
        
        return news_items[:1]
    
    def parse_polymerbranch(self, html: str, base_url: str) -> List[Dict]:
        """
        Parse https://polymerbranch.com/news/
        Берет последние 3 новости
        """
        news_items = []
        soup = BeautifulSoup(html, 'lxml')
        
        # Look for news items - common patterns
        selectors = [
            '.news-item', '.post-item', '.article-item',
            '[class*="news"]', '[class*="post"]',
            'article', '.card'
        ]
        
        articles = []
        for selector in selectors:
            articles = soup.select(selector)
            if articles:
                break
        
        if not articles:
            # Fallback: find all links that might be news
            articles = soup.find_all('a', href=lambda x: x and '/news/' in x)[:10]
        
        for article in articles[:3]:
            # Get title
            title_elem = article.find(['h1', 'h2', 'h3', 'a'], class_=lambda x: x and ('title' in x.lower() if x else False))
            if not title_elem:
                title_elem = article.find(['h1', 'h2', 'h3', 'a'])
            
            if not title_elem:
                continue
            
            title = title_elem.get_text(strip=True)[:200]
            if not title:
                continue
            
            # Get link
            link_elem = article.find('a', href=True)
            link = urljoin(base_url, link_elem['href']) if link_elem else base_url
            
            # Get content/description
            content_elem = article.find(['p', 'div'], class_=lambda x: x and ('content' in x.lower() or 'desc' in x.lower() if x else False))
            if not content_elem:
                content_elem = article.find('p')
            
            content = content_elem.get_text(strip=True)[:1000] if content_elem else title
            
            # Get date if available
            date_elem = article.find(['time', 'span'], class_=lambda x: x and ('date' in x.lower() or 'time' in x.lower() if x else False))
            pub_date = datetime.utcnow().isoformat()
            if date_elem:
                date_text = date_elem.get('datetime', date_elem.get_text(strip=True))
                if date_text:
                    pub_date = date_text
            
            news_item = {
                'title': title,
                'content': content,
                'date': pub_date,
                'source': 'polymerbranch.com',
                'source_type': 'website',
                'link': link,
                'media_url': None,
                'parser_type': 'polymerbranch'
            }
            news_items.append(news_item)
        
        return news_items[:3]
    
    def parse_plastinfo(self, html: str, base_url: str) -> List[Dict]:
        """
        Parse https://plastinfo.ru/information/news/
        Берет последние 3 новости
        """
        news_items = []
        soup = BeautifulSoup(html, 'lxml')
        
        # Plastinfo specific selectors
        selectors = [
            '.news-item', '.news_list .item', '.item-news',
            '[class*="news"]', 'article'
        ]
        
        articles = []
        for selector in selectors:
            articles = soup.select(selector)
            if articles:
                break
        
        if not articles:
            articles = soup.find_all('a', href=lambda x: x and '/news/' in x)[:10]
        
        for article in articles[:3]:
            title_elem = article.find(['h2', 'h3', 'a'], class_=lambda x: x and ('title' in x.lower() if x else False))
            if not title_elem:
                title_elem = article.find(['h2', 'h3', 'a'])
            
            if not title_elem:
                continue
            
            title = title_elem.get_text(strip=True)[:200]
            if not title:
                continue
            
            link_elem = article.find('a', href=True)
            link = urljoin(base_url, link_elem['href']) if link_elem else base_url
            
            content_elem = article.find(['p', 'div'], class_=lambda x: x and ('desc' in x.lower() or 'content' in x.lower() if x else False))
            if not content_elem:
                content_elem = article.find('p')
            
            content = content_elem.get_text(strip=True)[:1000] if content_elem else title
            
            date_elem = article.find(['time', 'span'], class_=lambda x: x and ('date' in x.lower() if x else False))
            pub_date = datetime.utcnow().isoformat()
            if date_elem:
                date_text = date_elem.get('datetime', date_elem.get_text(strip=True))
                if date_text:
                    pub_date = date_text
            
            news_item = {
                'title': title,
                'content': content,
                'date': pub_date,
                'source': 'plastinfo.ru',
                'source_type': 'website',
                'link': link,
                'media_url': None,
                'parser_type': 'plastinfo'
            }
            news_items.append(news_item)
        
        return news_items[:3]
    
    def parse_e_plastic(self, html: str, base_url: str) -> List[Dict]:
        """
        Parse https://e-plastic.ru/news/?PAGEN_1=2&SIZEN_1=20
        Берет последние 3 новости
        """
        news_items = []
        soup = BeautifulSoup(html, 'lxml')
        
        selectors = [
            '.news-item', '.news-detail', '[class*="news"]',
            'article', '.card', '.post'
        ]
        
        articles = []
        for selector in selectors:
            articles = soup.select(selector)
            if articles:
                break
        
        if not articles:
            articles = soup.find_all('a', href=lambda x: x and '/news/' in x)[:10]
        
        for article in articles[:3]:
            title_elem = article.find(['h2', 'h3', 'a'], class_=lambda x: x and ('title' in x.lower() if x else False))
            if not title_elem:
                title_elem = article.find(['h2', 'h3', 'a'])
            
            if not title_elem:
                continue
            
            title = title_elem.get_text(strip=True)[:200]
            if not title:
                continue
            
            link_elem = article.find('a', href=True)
            link = urljoin(base_url, link_elem['href']) if link_elem else base_url
            
            content_elem = article.find(['p', 'div'], class_=lambda x: x and ('desc' in x.lower() if x else False))
            if not content_elem:
                content_elem = article.find('p')
            
            content = content_elem.get_text(strip=True)[:1000] if content_elem else title
            
            date_elem = article.find(['time', 'span'], class_=lambda x: x and ('date' in x.lower() if x else False))
            pub_date = datetime.utcnow().isoformat()
            if date_elem:
                date_text = date_elem.get('datetime', date_elem.get_text(strip=True))
                if date_text:
                    pub_date = date_text
            
            news_item = {
                'title': title,
                'content': content,
                'date': pub_date,
                'source': 'e-plastic.ru',
                'source_type': 'website',
                'link': link,
                'media_url': None,
                'parser_type': 'e_plastic'
            }
            news_items.append(news_item)
        
        return news_items[:3]
    
    def parse_unipack_news(self, html: str, base_url: str) -> List[Dict]:
        """
        Parse https://news.unipack.ru/
        Берет последние 3 новости
        """
        news_items = []
        soup = BeautifulSoup(html, 'lxml')
        
        selectors = [
            '.news-item', '.post-item', '.article-item',
            '[class*="news"]', 'article', '.card'
        ]
        
        articles = []
        for selector in selectors:
            articles = soup.select(selector)
            if articles:
                break
        
        if not articles:
            articles = soup.find_all('a', href=True)[:10]
        
        for article in articles[:3]:
            title_elem = article.find(['h2', 'h3', 'a'], class_=lambda x: x and ('title' in x.lower() if x else False))
            if not title_elem:
                title_elem = article.find(['h2', 'h3', 'a'])
            
            if not title_elem:
                continue
            
            title = title_elem.get_text(strip=True)[:200]
            if not title:
                continue
            
            link_elem = article.find('a', href=True)
            link = urljoin(base_url, link_elem['href']) if link_elem else base_url
            
            content_elem = article.find(['p', 'div'], class_=lambda x: x and ('desc' in x.lower() if x else False))
            if not content_elem:
                content_elem = article.find('p')
            
            content = content_elem.get_text(strip=True)[:1000] if content_elem else title
            
            date_elem = article.find(['time', 'span'], class_=lambda x: x and ('date' in x.lower() if x else False))
            pub_date = datetime.utcnow().isoformat()
            if date_elem:
                date_text = date_elem.get('datetime', date_elem.get_text(strip=True))
                if date_text:
                    pub_date = date_text
            
            news_item = {
                'title': title,
                'content': content,
                'date': pub_date,
                'source': 'news.unipack.ru',
                'source_type': 'website',
                'link': link,
                'media_url': None,
                'parser_type': 'unipack_news'
            }
            news_items.append(news_item)
        
        return news_items[:3]
    
    def parse_generic_news(self, html: str, base_url: str) -> List[Dict]:
        """
        Parse news from a generic website.
        Fallback parser for unknown sites.
        """
        news_items = []
        soup = BeautifulSoup(html, 'lxml')
        
        article_selectors = [
            'article', '.news-item', '.post', '.article',
            '[class*="news"]', '[class*="post"]', '[class*="article"]'
        ]
        
        articles = []
        for selector in article_selectors:
            articles = soup.select(selector)
            if articles:
                break
        
        for article in articles[:MAX_NEWS_PER_RUN]:
            title_elem = article.find(['h1', 'h2', 'h3', 'a'], class_=lambda x: x and ('title' in x.lower() if x else False))
            if not title_elem:
                title_elem = article.find(['h1', 'h2', 'h3', 'a'])
            
            if not title_elem:
                continue
            
            title = title_elem.get_text(strip=True)[:200]
            
            link_elem = article.find('a', href=True)
            link = urljoin(base_url, link_elem['href']) if link_elem else base_url
            
            content_elem = article.find(['p', 'div'], class_=lambda x: x and ('content' in x.lower() if x else False))
            if not content_elem:
                content_elem = article.find('p')
            
            content = content_elem.get_text(strip=True)[:1000] if content_elem else title
            
            date_elem = article.find(['time', 'span'], class_=lambda x: x and ('date' in x.lower() if x else False))
            pub_date = datetime.utcnow().isoformat()
            if date_elem:
                date_text = date_elem.get('datetime', date_elem.get_text(strip=True))
                if date_text:
                    pub_date = date_text
            
            news_item = {
                'title': title,
                'content': content,
                'date': pub_date,
                'source': urlparse(base_url).netloc,
                'source_type': 'website',
                'link': link,
                'media_url': None,
                'parser_type': 'generic'
            }
            news_items.append(news_item)
        
        return news_items
    
    async def parse_site(self, url: str, hours_back: int = 24) -> List[Dict]:
        """
        Parse news from a website using appropriate parser.
        
        Args:
            url: Website URL to parse
            hours_back: How many hours back to collect (used for filtering)
            
        Returns:
            List of news items
        """
        news_items = []
        
        try:
            html = await self.fetch_page(url)
            if html:
                # Determine which parser to use based on URL
                if 'dzen.ru/proplast' in url:
                    news_items = self.parse_dzen_proplast(html, url)
                elif 'dzen.ru/okstanok' in url:
                    news_items = self.parse_dzen_okstanok(html, url)
                elif 'polymerbranch.com/news' in url:
                    news_items = self.parse_polymerbranch(html, url)
                elif 'plastinfo.ru/information/news' in url:
                    news_items = self.parse_plastinfo(html, url)
                elif 'e-plastic.ru/news' in url:
                    news_items = self.parse_e_plastic(html, url)
                elif 'news.unipack.ru' in url:
                    news_items = self.parse_unipack_news(html, url)
                else:
                    news_items = self.parse_generic_news(html, url)
        except Exception as e:
            print(f"Error parsing site {url}: {str(e)}")
        
        return news_items
    
    async def parse_sites(self, url_list: List[str], hours_back: int = 24) -> List[Dict]:
        """
        Parse multiple websites.
        
        Args:
            url_list: List of website URLs
            hours_back: How many hours back to collect
            
        Returns:
            Combined list of news items from all sites
        """
        all_news = []
        
        tasks = [self.parse_site(url, hours_back) for url in url_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_news.extend(result)
            elif isinstance(result, Exception):
                print(f"Parse error: {str(result)}")
        
        # Sort by date (newest first)
        all_news.sort(key=lambda x: x['date'], reverse=True)
        
        return all_news
    
    async def test_connection(self) -> bool:
        """Test if the parser can fetch web pages."""
        try:
            await self.connect()
            html = await self.fetch_page('https://example.com')
            return html is not None
        except Exception as e:
            print(f"Connection test failed: {str(e)}")
            return False


# Example usage
if __name__ == '__main__':
    async def main():
        parser = WebParser()
        
        # Test parsing different sites
        urls = [
            'https://dzen.ru/proplast',
            'https://polymerbranch.com/news/',
        ]
        
        for url in urls:
            print(f"\n=== Parsing {url} ===")
            news = await parser.parse_site(url, hours_back=24)
            
            for item in news[:2]:
                print(f"Title: {item['title']}")
                print(f"Date: {item['date']}")
                print(f"Link: {item['link']}")
                print("-" * 50)
        
        await parser.disconnect()
    
    asyncio.run(main())
