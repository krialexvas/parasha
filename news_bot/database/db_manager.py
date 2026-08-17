"""
Database manager using SQLite for storing sources, schedules, and settings.
"""
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Optional
import aiosqlite

from config import DATABASE_PATH


class DatabaseManager:
    """SQLite database manager for bot data."""
    
    def __init__(self):
        self.db_path = DATABASE_PATH
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self):
        """Initialize database connection and create tables."""
        if not self._connection:
            self._connection = await aiosqlite.connect(self.db_path)
            self._connection.row_factory = aiosqlite.Row
            await self._init_db()
    
    async def disconnect(self):
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    async def _init_db(self):
        """Create database tables if they don't exist."""
        async with self._connection.cursor() as cursor:
            # Sources table (Telegram channels and websites)
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    source_type TEXT NOT NULL CHECK(source_type IN ('telegram', 'website')),
                    title TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Schedule table
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    day_of_week INTEGER NOT NULL CHECK(day_of_week BETWEEN 0 AND 6),
                    hour INTEGER NOT NULL CHECK(hour BETWEEN 0 AND 23),
                    minute INTEGER NOT NULL CHECK(minute BETWEEN 0 AND 59),
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Settings table
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # News history table
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS news_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT,
                    source_id INTEGER,
                    source_type TEXT,
                    original_link TEXT,
                    parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed INTEGER DEFAULT 0,
                    folder_path TEXT,
                    FOREIGN KEY (source_id) REFERENCES sources(id)
                )
            ''')
            
            await self._connection.commit()
    
    # ==================== SOURCES ====================
    
    async def add_source(
        self,
        url: str,
        source_type: str,
        title: Optional[str] = None
    ) -> bool:
        """
        Add a new news source.
        
        Args:
            url: Channel username or website URL
            source_type: 'telegram' or 'website'
            title: Optional display title
            
        Returns:
            True if added successfully
        """
        try:
            async with self._connection.cursor() as cursor:
                await cursor.execute('''
                    INSERT INTO sources (url, source_type, title)
                    VALUES (?, ?, ?)
                ''', (url, source_type, title))
                await self._connection.commit()
                return True
        except aiosqlite.IntegrityError:
            # Source already exists
            return False
        except Exception as e:
            print(f"Error adding source: {str(e)}")
            return False
    
    async def remove_source(self, source_id: int) -> bool:
        """Remove a source by ID."""
        try:
            async with self._connection.cursor() as cursor:
                await cursor.execute('DELETE FROM sources WHERE id = ?', (source_id,))
                await self._connection.commit()
                return True
        except Exception as e:
            print(f"Error removing source: {str(e)}")
            return False
    
    async def deactivate_source(self, source_id: int) -> bool:
        """Deactivate a source without deleting it."""
        try:
            async with self._connection.cursor() as cursor:
                await cursor.execute('''
                    UPDATE sources SET is_active = 0, updated_at = ? WHERE id = ?
                ''', (datetime.now(), source_id))
                await self._connection.commit()
                return True
        except Exception as e:
            print(f"Error deactivating source: {str(e)}")
            return False
    
    async def get_sources(
        self,
        source_type: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict]:
        """
        Get list of configured sources.
        
        Args:
            source_type: Filter by type ('telegram' or 'website')
            active_only: Only return active sources
            
        Returns:
            List of source dictionaries
        """
        async with self._connection.cursor() as cursor:
            query = 'SELECT * FROM sources WHERE 1=1'
            params = []
            
            if active_only:
                query += ' AND is_active = 1'
            
            if source_type:
                query += ' AND source_type = ?'
                params.append(source_type)
            
            query += ' ORDER BY created_at DESC'
            
            await cursor.execute(query, params)
            rows = await cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    async def get_telegram_channels(self) -> List[str]:
        """Get list of Telegram channel usernames."""
        sources = await self.get_sources('telegram')
        return [s['url'] for s in sources]
    
    async def get_websites(self) -> List[str]:
        """Get list of website URLs."""
        sources = await self.get_sources('website')
        return [s['url'] for s in sources]
    
    # ==================== SCHEDULES ====================
    
    async def add_schedule(
        self,
        day_of_week: int,
        hour: int,
        minute: int
    ) -> bool:
        """
        Add a new schedule entry.
        
        Args:
            day_of_week: 0=Monday, 6=Sunday
            hour: Hour (0-23)
            minute: Minute (0-59)
            
        Returns:
            True if added successfully
        """
        try:
            async with self._connection.cursor() as cursor:
                await cursor.execute('''
                    INSERT INTO schedules (day_of_week, hour, minute)
                    VALUES (?, ?, ?)
                ''', (day_of_week, hour, minute))
                await self._connection.commit()
                return True
        except Exception as e:
            print(f"Error adding schedule: {str(e)}")
            return False
    
    async def remove_schedule(self, schedule_id: int) -> bool:
        """Remove a schedule entry."""
        try:
            async with self._connection.cursor() as cursor:
                await cursor.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
                await self._connection.commit()
                return True
        except Exception as e:
            print(f"Error removing schedule: {str(e)}")
            return False
    
    async def get_schedules(self, active_only: bool = True) -> List[Dict]:
        """
        Get all scheduled tasks.
        
        Returns:
            List of schedule dictionaries
        """
        async with self._connection.cursor() as cursor:
            query = 'SELECT * FROM schedules'
            params = []
            
            if active_only:
                query += ' WHERE is_active = 1'
            
            query += ' ORDER BY day_of_week, hour, minute'
            
            await cursor.execute(query, params)
            rows = await cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    async def deactivate_schedule(self, schedule_id: int) -> bool:
        """Deactivate a schedule without deleting it."""
        try:
            async with self._connection.cursor() as cursor:
                await cursor.execute('''
                    UPDATE schedules SET is_active = 0 WHERE id = ?
                ''', (schedule_id,))
                await self._connection.commit()
                return True
        except Exception as e:
            print(f"Error deactivating schedule: {str(e)}")
            return False
    
    # ==================== SETTINGS ====================
    
    async def set_setting(self, key: str, value: any) -> bool:
        """Store a setting value."""
        try:
            async with self._connection.cursor() as cursor:
                await cursor.execute('''
                    INSERT OR REPLACE INTO settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                ''', (key, json.dumps(value), datetime.now()))
                await self._connection.commit()
                return True
        except Exception as e:
            print(f"Error setting {key}: {str(e)}")
            return False
    
    async def get_setting(self, key: str, default: any = None) -> any:
        """Retrieve a setting value."""
        try:
            async with self._connection.cursor() as cursor:
                await cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
                row = await cursor.fetchone()
                
                if row:
                    return json.loads(row['value'])
                return default
        except Exception as e:
            print(f"Error getting {key}: {str(e)}")
            return default
    
    # ==================== NEWS HISTORY ====================
    
    async def save_news_to_history(
        self,
        title: str,
        content: str,
        source_id: Optional[int],
        source_type: str,
        original_link: Optional[str] = None
    ) -> Optional[int]:
        """
        Save parsed news to history.
        
        Returns:
            News item ID or None if failed
        """
        try:
            async with self._connection.cursor() as cursor:
                await cursor.execute('''
                    INSERT INTO news_history 
                    (title, content, source_id, source_type, original_link)
                    VALUES (?, ?, ?, ?, ?)
                ''', (title, content, source_id, source_type, original_link))
                await self._connection.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Error saving news to history: {str(e)}")
            return None
    
    async def mark_news_processed(
        self,
        news_id: int,
        folder_path: str
    ) -> bool:
        """Mark news item as processed and store folder path."""
        try:
            async with self._connection.cursor() as cursor:
                await cursor.execute('''
                    UPDATE news_history 
                    SET processed = 1, folder_path = ?
                    WHERE id = ?
                ''', (folder_path, news_id))
                await self._connection.commit()
                return True
        except Exception as e:
            print(f"Error marking news processed: {str(e)}")
            return False
    
    async def get_unprocessed_news(self, limit: int = 50) -> List[Dict]:
        """Get list of unprocessed news items."""
        async with self._connection.cursor() as cursor:
            await cursor.execute('''
                SELECT * FROM news_history 
                WHERE processed = 0 
                ORDER BY parsed_at DESC 
                LIMIT ?
            ''', (limit,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # ==================== UTILITY ====================
    
    async def get_stats(self) -> Dict:
        """Get database statistics."""
        stats = {}
        
        async with self._connection.cursor() as cursor:
            # Count sources
            await cursor.execute('SELECT COUNT(*) as count FROM sources WHERE is_active = 1')
            stats['active_sources'] = (await cursor.fetchone())['count']
            
            # Count schedules
            await cursor.execute('SELECT COUNT(*) as count FROM schedules WHERE is_active = 1')
            stats['active_schedules'] = (await cursor.fetchone())['count']
            
            # Count news history
            await cursor.execute('SELECT COUNT(*) as count FROM news_history')
            stats['total_news'] = (await cursor.fetchone())['count']
            
            await cursor.execute('SELECT COUNT(*) as count FROM news_history WHERE processed = 1')
            stats['processed_news'] = (await cursor.fetchone())['count']
        
        return stats


# Example usage
if __name__ == '__main__':
    async def main():
        db = DatabaseManager()
        await db.connect()
        
        # Add test sources
        await db.add_source('@durov', 'telegram', 'Pavel Durov')
        await db.add_source('https://example.com/news', 'website', 'Example News')
        
        # Add test schedule (Monday at 9:00)
        await db.add_schedule(day_of_week=0, hour=9, minute=0)
        
        # Get all sources
        sources = await db.get_sources()
        print("Sources:", sources)
        
        # Get all schedules
        schedules = await db.get_schedules()
        print("Schedules:", schedules)
        
        # Get stats
        stats = await db.get_stats()
        print("Stats:", stats)
        
        await db.disconnect()
    
    asyncio.run(main())
