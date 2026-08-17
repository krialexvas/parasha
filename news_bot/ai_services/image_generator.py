"""
Image generation service using Kandinsky API (FusionBrain).
Creates illustrations for news articles.
"""
import asyncio
from typing import Optional, Dict, Any
import aiohttp
import base64
from pathlib import Path

from config import (
    KANDINSKY_API_KEY,
    KANDINSKY_SECRET_KEY,
    REQUEST_TIMEOUT,
    OUTPUT_DIR
)


class ImageGenerator:
    """Service for generating images using Kandinsky AI."""
    
    def __init__(self):
        self.api_key = KANDINSKY_API_KEY
        self.secret_key = KANDINSKY_SECRET_KEY
        self.base_url = 'https://api-key.fusionbrain.ai'
        self.session = None
    
    async def connect(self):
        """Initialize HTTP session."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT * 5)  # Longer for image gen
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def disconnect(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Generate authentication headers for API requests."""
        return {
            'X-Key': f'Key {self.api_key}',
            'X-Secret': f'Secret {self.secret_key}',
        }
    
    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = '',
        width: int = 1024,
        height: int = 1024,
        samples: int = 1,
        steps: int = 30
    ) -> Optional[bytes]:
        """
        Generate image from text prompt.
        
        Args:
            prompt: Text description of the image
            negative_prompt: What to exclude from the image
            width: Image width in pixels
            height: Image height in pixels
            samples: Number of images to generate
            steps: Generation steps (more = better quality, slower)
            
        Returns:
            Image bytes or None if failed
        """
        try:
            await self.connect()
            
            # Step 1: Submit generation request
            generation_data = {
                "type": "GENERATE",
                "numImages": samples,
                "width": width,
                "height": height,
                "steps": steps,
                "prompt": prompt,
                "negativePrompt": negative_prompt
            }
            
            headers = self._get_auth_headers()
            headers['Content-Type'] = 'application/json'
            
            async with self.session.post(
                f'{self.base_url}/key/api/v1/text2image/run',
                json=generation_data,
                headers=headers
            ) as response:
                if response.status != 200:
                    print(f"Kandinsky submit error: {response.status}")
                    return None
                
                result = await response.json()
                uuid = result.get('uuid')
                
                if not uuid:
                    print("No UUID in response")
                    return None
            
            # Step 2: Poll for completion
            max_attempts = 30
            delay = 5  # seconds
            
            for attempt in range(max_attempts):
                await asyncio.sleep(delay)
                
                async with self.session.get(
                    f'{self.base_url}/key/api/v1/text2image/status/{uuid}',
                    headers=headers
                ) as status_response:
                    if status_response.status != 200:
                        continue
                    
                    status_result = await status_response.json()
                    status = status_result.get('status')
                    
                    if status == 'DONE':
                        # Extract image from base64
                        images = status_result.get('images', [])
                        if images:
                            image_base64 = images[0]
                            image_bytes = base64.b64decode(image_base64)
                            return image_bytes
                    elif status == 'FAIL':
                        print(f"Generation failed: {status_result}")
                        return None
                    # Status is PENDING or RUNNING - continue polling
            
            print("Image generation timeout")
            return None
            
        except Exception as e:
            print(f"Error generating image: {str(e)}")
            return None
    
    async def generate_news_illustration(
        self,
        title: str,
        content: str,
        style: str = 'realistic'
    ) -> Optional[bytes]:
        """
        Generate an illustration for a news article.
        
        Args:
            title: Article title
            content: Article content
            style: Art style ('realistic', 'illustration', 'digital_art', etc.)
            
        Returns:
            Image bytes or None if failed
        """
        # Create prompt from title and content
        # Truncate content to avoid token limits
        content_snippet = content[:500] if len(content) > 500 else content
        
        # Build prompt based on style
        if style == 'realistic':
            style_desc = "фотореалистичное изображение, высокое качество, профессиональная фотография"
        elif style == 'illustration':
            style_desc = "стильная иллюстрация, векторная графика, современный дизайн"
        elif style == 'digital_art':
            style_desc = "цифровое искусство, концепт-арт, детализированная работа"
        else:
            style_desc = "качественное изображение"
        
        # Create descriptive prompt
        prompt = (
            f"Новостная иллюстрация на тему: {title}. "
            f"{content_snippet}. "
            f"{style_desc}, высокое разрешение, профессиональное качество"
        )
        
        # Negative prompt to avoid common issues
        negative_prompt = (
            "текст, надписи, вода, размыто, низкое качество, искажения, "
            "деформации, лишние пальцы, плохая анатомия"
        )
        
        return await self.generate_image(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=1024,
            height=768,  # Landscape orientation for news
            samples=1,
            steps=30
        )
    
    async def save_image(
        self,
        image_bytes: bytes,
        filename: str,
        folder_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Save generated image to file.
        
        Args:
            image_bytes: Image data
            filename: Filename (without extension)
            folder_path: Directory to save in
            
        Returns:
            Full path to saved file or None if failed
        """
        try:
            if folder_path is None:
                folder_path = OUTPUT_DIR
            
            # Ensure directory exists
            Path(folder_path).mkdir(parents=True, exist_ok=True)
            
            # Save as JPG
            filepath = Path(folder_path) / f"{filename}.jpg"
            
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            return str(filepath)
            
        except Exception as e:
            print(f"Error saving image: {str(e)}")
            return None
    
    async def test_connection(self) -> bool:
        """Test API connection with a simple generation request."""
        test_prompt = "тестовое изображение, простой объект"
        result = await self.generate_image(test_prompt, max_attempts=5)
        return result is not None


# Example usage
if __name__ == '__main__':
    async def main():
        generator = ImageGenerator()
        
        # Generate image for a news article
        image_bytes = await generator.generate_news_illustration(
            title="Новый смартфон представлен",
            content="Компания выпустила революционное устройство с улучшенной камерой и процессором."
        )
        
        if image_bytes:
            # Save the image
            filepath = await generator.save_image(image_bytes, "test_news_image")
            print(f"Image saved to: {filepath}")
        else:
            print("Image generation failed")
        
        await generator.disconnect()
    
    asyncio.run(main())
