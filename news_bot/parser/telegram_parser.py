"""
Telegram channel parser using Telethon.
Collects recent posts from configured Telegram channels.
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from telethon import TelegramClient
from telethon.tl.types import Message

from config import (
    TELETHON_API_ID,
    TELETHON_API_HASH,
    MAX_NEWS_PER_RUN,
    REQUEST_TIMEOUT
)


class TelegramParser:
    """Parser for Telegram channels."""
    
    def __init__(self):
        self.client = None
        self.session_name = 'news_parser_session'
        
    async def connect(self):
        """Initialize and connect the Telegram client."""
        if not self.client:
            self.client = TelegramClient(
                self.session_name,
                TELETHON_API_ID,
                TELETHON_API_HASH
            )
            await self.client.start()
    
    async def disconnect(self):
        """Disconnect the Telegram client."""
        if self.client:
            await self.client.disconnect()
            self.client = None
    
    async def parse_channel(
        self, 
        channel_username: str, 
        hours_back: int = 24
    ) -> List[Dict]:
        """
        Parse recent posts from a Telegram channel.
        
        Args:
            channel_username: Channel username (with or without @)
            hours_back: How many hours back to collect posts
            
        Returns:
            List of news items with title, content, date, and link
        """
        news_items = []
        
        try:
            await self.connect()
            
            # Normalize channel username
            if not channel_username.startswith('@'):
                channel_username = f'@{channel_username}'
            
            # Get the channel entity
            channel = await self.client.get_entity(channel_username)
            
            # Calculate cutoff date
            cutoff_date = datetime.utcnow() - timedelta(hours=hours_back)
            
            # Fetch recent messages
            messages = await self.client.get_messages(
                channel,
                limit=MAX_NEWS_PER_RUN,
                min_date=cutoff_date
            )
            
            for msg in messages:
                if not msg.message or msg.message.strip() == '':
                    continue
                
                # Extract media if present
                media_url = None
                if msg.media:
                    # For photos, we could download them, but for now just note presence
                    media_url = f"https://t.me/{channel_username}/{msg.id}"
                
                # Create news item
                news_item = {
                    'title': msg.message.split('\n')[0][:100],  # First line as title
                    'content': msg.message,
                    'date': msg.date.isoformat(),
                    'source': channel_username,
                    'source_type': 'telegram',
                    'link': f"https://t.me/{channel_username}/{msg.id}",
                    'media_url': media_url,
                    'message_id': msg.id
                }
                
                news_items.append(news_item)
                
        except Exception as e:
            print(f"Error parsing channel {channel_username}: {str(e)}")
        
        return news_items
    
    async def parse_channels(
        self, 
        channel_list: List[str],
        hours_back: int = 24
    ) -> List[Dict]:
        """
        Parse multiple Telegram channels.
        
        Args:
            channel_list: List of channel usernames
            hours_back: How many hours back to collect posts
            
        Returns:
            Combined list of news items from all channels
        """
        all_news = []
        
        for channel in channel_list:
            news = await self.parse_channel(channel, hours_back)
            all_news.extend(news)
            # Small delay to avoid rate limiting
            await asyncio.sleep(1)
        
        # Sort by date (newest first)
        all_news.sort(key=lambda x: x['date'], reverse=True)
        
        # Limit total results
        return all_news[:MAX_NEWS_PER_RUN]
    
    async def test_connection(self) -> bool:
        """Test if the Telegram client can connect."""
        try:
            await self.connect()
            return True
        except Exception as e:
            print(f"Connection test failed: {str(e)}")
            return False


# Example usage
if __name__ == '__main__':
    async def main():
        parser = TelegramParser()
        
        # Test parsing a channel
        news = await parser.parse_channel('@durov', hours_back=24)
        
        for item in news[:3]:
            print(f"Title: {item['title']}")
            print(f"Date: {item['date']}")
            print(f"Link: {item['link']}")
            print("-" * 50)
        
        await parser.disconnect()
    
    asyncio.run(main())
