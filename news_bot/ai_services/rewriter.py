"""
Text rewriting service using TEXT.ru API.
Provides unique rewording of news articles.
"""
import asyncio
from typing import Optional, Dict
import aiohttp
from hashlib import md5

from config import TEXT_RU_API_KEY, REQUEST_TIMEOUT


class TextRewriter:
    """Service for rewriting text using TEXT.ru API."""
    
    def __init__(self):
        self.api_key = TEXT_RU_API_KEY
        self.base_url = 'https://api.text.ru/antiplagiat'
        self.session = None
    
    async def connect(self):
        """Initialize HTTP session."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT * 3)  # Longer timeout for API
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def disconnect(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    def _get_md5_hash(self, text: str) -> str:
        """Generate MD5 hash of text for API request."""
        return md5(text.encode('utf-8')).hexdigest()
    
    async def submit_text(self, text: str) -> Optional[str]:
        """
        Submit text for rewriting to TEXT.ru API.
        
        Args:
            text: Text content to rewrite
            
        Returns:
            Job UID or None if failed
        """
        try:
            await self.connect()
            
            data = {
                'api_key': self.api_key,
                'text': text,
                'json': 1
            }
            
            async with self.session.post(
                f'{self.base_url}/rewrite',
                data=data
            ) as response:
                result = await response.json()
                
                if result.get('status') == 'success':
                    return result.get('uid')
                else:
                    print(f"TEXT.ru submit error: {result}")
                    return None
                    
        except Exception as e:
            print(f"Error submitting text to TEXT.ru: {str(e)}")
            return None
    
    async def check_status(self, uid: str) -> Optional[Dict]:
        """
        Check rewriting job status.
        
        Args:
            uid: Job UID from submit_text
            
        Returns:
            Job status and result or None if failed
        """
        try:
            await self.connect()
            
            data = {
                'api_key': self.api_key,
                'uid': uid,
                'json': 1
            }
            
            async with self.session.post(
                f'{self.base_url}/rewrite',
                data=data
            ) as response:
                result = await response.json()
                return result
                
        except Exception as e:
            print(f"Error checking TEXT.ru status: {str(e)}")
            return None
    
    async def rewrite_text(
        self, 
        text: str, 
        max_attempts: int = 20,
        delay_seconds: int = 3
    ) -> Optional[str]:
        """
        Rewrite text using TEXT.ru API with polling.
        
        Args:
            text: Original text to rewrite
            max_attempts: Maximum polling attempts
            delay_seconds: Delay between status checks
            
        Returns:
            Rewritten text or None if failed
        """
        # Submit text
        uid = await self.submit_text(text)
        if not uid:
            return None
        
        # Poll for results
        for attempt in range(max_attempts):
            await asyncio.sleep(delay_seconds)
            
            result = await self.check_status(uid)
            if not result:
                continue
            
            status = result.get('status')
            
            if status == 'success':
                rewritten_text = result.get('rewrites', [{}])[0].get('text')
                if rewritten_text:
                    return rewritten_text
            elif status == 'error':
                print(f"TEXT.ru processing error: {result}")
                return None
            # status == 'pending' or 'queue' - continue polling
        
        print("TEXT.ru rewriting timeout")
        return None
    
    async def rewrite_news_article(
        self,
        title: str,
        content: str,
        style: str = 'news'
    ) -> Dict[str, str]:
        """
        Rewrite a complete news article (title + content).
        
        Args:
            title: Article title
            content: Article content
            style: Writing style ('news', 'blog', 'formal', etc.)
            
        Returns:
            Dictionary with rewritten title and content
        """
        # Combine title and content for context
        full_text = f"{title}\n\n{content}"
        
        # Add style instruction
        if style == 'news':
            instruction = "Перепиши этот текст в стиле новостной статьи, сохранив все факты и цифры. Сделай текст уникальным, но информативным."
        elif style == 'blog':
            instruction = "Перепиши этот текст в стиле блога, сделай его более живым и интересным для читателей."
        else:
            instruction = "Перепиши этот текст, сохранив основной смысл, но сделав его уникальным."
        
        enhanced_text = f"{instruction}\n\n{full_text}"
        
        rewritten = await self.rewrite_text(enhanced_text)
        
        if rewritten:
            # Try to separate title and content
            lines = rewritten.split('\n\n', 1)
            new_title = lines[0][:150] if lines else title
            new_content = lines[1] if len(lines) > 1 else rewritten
            
            return {
                'title': new_title,
                'content': new_content,
                'original_title': title,
                'original_content': content,
                'success': True
            }
        else:
            return {
                'title': title,
                'content': content,
                'original_title': title,
                'original_content': content,
                'success': False,
                'error': 'Rewriting failed'
            }
    
    async def test_connection(self) -> bool:
        """Test API connection with a simple request."""
        test_text = "Тестовый текст для проверки работы API сервиса."
        result = await self.rewrite_text(test_text, max_attempts=5)
        return result is not None


# Example usage
if __name__ == '__main__':
    async def main():
        rewriter = TextRewriter()
        
        original = """
        Компания Apple представила новый iPhone с революционными возможностями.
        Устройство оснащено процессором A17 Pro и улучшенной камерой.
        Цена начинается от 999 долларов.
        """
        
        result = await rewriter.rewrite_news_article(
            "Apple представила новый iPhone",
            original,
            style='news'
        )
        
        print(f"Original Title: {result['original_title']}")
        print(f"New Title: {result['title']}")
        print(f"New Content: {result['content']}")
        print(f"Success: {result['success']}")
        
        await rewriter.disconnect()
    
    asyncio.run(main())
