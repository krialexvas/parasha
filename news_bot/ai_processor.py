"""
AI Processing Module
Handles text rewriting and image generation using AI APIs
"""

import logging
import aiohttp
import asyncio
from typing import List, Optional, Tuple
from news_collector import NewsItem

logger = logging.getLogger(__name__)


class TextRuRewriter:
    """Text rewriting using Text.ru API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.text.ru/uniq"
    
    async def rewrite_text(self, text: str, max_attempts: int = 3) -> Optional[str]:
        """
        Rewrite text using Text.ru API
        
        Note: Text.ru primarily offers uniqueness checking. 
        For actual rewriting, we'll use a prompt-based approach with their API
        or fallback to alternative methods.
        """
        
        # Text.ru API is mainly for uniqueness checking
        # For rewriting, we need to implement our own logic or use another service
        # This is a simplified version - in production you'd want more robust handling
        
        logger.info(f"Rewriting text with Text.ru (length: {len(text)})")
        
        try:
            # Text.ru uniqueness check endpoint
            async with aiohttp.ClientSession() as session:
                # First, submit text for analysis
                submit_data = {
                    'api_key': self.api_key,
                    'text': text,
                    'submit': 'y'
                }
                
                async with session.post(f"{self.base_url}/", data=submit_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        job_id = result.get('id')
                        
                        if job_id:
                            # Poll for results
                            for _ in range(max_attempts):
                                await asyncio.sleep(2)
                                
                                status_data = {
                                    'api_key': self.api_key,
                                    'id': job_id
                                }
                                
                                async with session.post(f"{self.base_url}/", data=status_data) as status_response:
                                    if status_response.status == 200:
                                        status_result = await status_response.json()
                                        
                                        if status_result.get('status') == 'success':
                                            # Text.ru provides uniqueness score but not rewriting
                                            # We'll return the original text with a note
                                            uniqueness = status_result.get('perc_uniq', 0)
                                            logger.info(f"Text uniqueness: {uniqueness}%")
                                            
                                            # For actual rewriting, we need to implement custom logic
                                            # This is a placeholder - you should integrate with 
                                            # a proper rewriting API like OpenAI GPT
                                            return self._simple_rewrite(text)
                            
                            logger.warning("Text.ru processing timeout")
                            return self._simple_rewrite(text)
                    else:
                        logger.error(f"Text.ru API error: {response.status}")
                        return self._simple_rewrite(text)
        
        except Exception as e:
            logger.error(f"Error in Text.ru rewriting: {e}")
            return self._simple_rewrite(text)
    
    def _simple_rewrite(self, text: str) -> str:
        """
        Simple text rewriting as fallback
        In production, replace this with actual AI rewriting (GPT-4, etc.)
        """
        # This is a very basic rewrite - NOT recommended for production
        # You should integrate with OpenAI GPT-4 or similar for quality rewrites
        
        synonyms = {
            'полимеры': 'полимерные материалы',
            'цены': 'стоимость',
            'рынок': 'рыночная ситуация',
            'производство': 'производственный процесс',
            'компания': 'организация',
            'продукция': 'изделия',
            'увеличение': 'рост',
            'снижение': 'падение',
        }
        
        rewritten = text
        for original, synonym in synonyms.items():
            rewritten = rewritten.replace(original, synonym)
        
        return rewritten


class OpenAIRewriter:
    """Text rewriting using OpenAI GPT API (recommended for quality)"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.model = "gpt-4o-mini"  # or gpt-4, gpt-3.5-turbo
    
    async def rewrite_text(self, text: str) -> Optional[str]:
        """Rewrite text using GPT model"""
        
        prompt = f"""Перепиши следующий текст новости в более интересном и engaging стиле, 
сохранив все ключевые факты и цифры. Сделай текст уникальным, но информативным.
Длина текста должна быть примерно такой же.

Исходный текст:
{text}

Перепиши новость:"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Ты профессиональный журналист и копирайтер."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        rewritten = result['choices'][0]['message']['content']
                        logger.info("Successfully rewrote text with GPT")
                        return rewritten.strip()
                    else:
                        error_text = await response.text()
                        logger.error(f"OpenAI API error: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error in OpenAI rewriting: {e}")
            return None


class ImageGenerator:
    """Generate images using AI APIs"""
    
    def __init__(self, api_key: str, provider: str = "openai"):
        self.api_key = api_key
        self.provider = provider
        
        if provider == "openai":
            self.base_url = "https://api.openai.com/v1/images/generations"
        elif provider == "stability":
            self.base_url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    async def generate_image(self, prompt: str, news_title: str) -> Optional[str]:
        """
        Generate an image based on the news content
        
        Returns: URL or path to generated image, or None if failed
        """
        
        # Create a detailed prompt for image generation
        image_prompt = f"""Professional news illustration, high quality, detailed: {prompt}"""
        
        if self.provider == "openai":
            return await self._generate_dalle(image_prompt)
        elif self.provider == "stability":
            return await self._generate_stability(image_prompt)
        
        return None
    
    async def _generate_dalle(self, prompt: str) -> Optional[str]:
        """Generate image using DALL-E 3"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "quality": "standard"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        image_url = result['data'][0]['url']
                        logger.info(f"Generated image with DALL-E: {image_url}")
                        return image_url
                    else:
                        error_text = await response.text()
                        logger.error(f"DALL-E API error: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error in DALL-E generation: {e}")
            return None
    
    async def _generate_stability(self, prompt: str) -> Optional[bytes]:
        """Generate image using Stability AI"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "image/*"
        }
        
        payload = {
            "text_prompts": [{"text": prompt}],
            "cfg_scale": 7,
            "height": 1024,
            "width": 1024,
            "samples": 1,
            "steps": 30
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        logger.info("Generated image with Stability AI")
                        return image_data
                    else:
                        error_text = await response.text()
                        logger.error(f"Stability AI error: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error in Stability AI generation: {e}")
            return None


class NewsProcessor:
    """Main class for processing news with AI"""
    
    def __init__(self, text_api_key: str = None, image_api_key: str = None,
                 text_provider: str = "openai", image_provider: str = "openai"):
        """
        Initialize processors
        
        Args:
            text_api_key: API key for text rewriting service
            image_api_key: API key for image generation service
            text_provider: 'openai' or 'text_ru'
            image_provider: 'openai' or 'stability'
        """
        
        # Try to load from config if not provided
        if text_api_key is None or image_api_key is None:
            try:
                from config import OPENAI_API_KEY, TEXT_RU_API_KEY, STABILITY_API_KEY
                
                if text_provider == "openai" and text_api_key is None:
                    if OPENAI_API_KEY and OPENAI_API_KEY != "YOUR_OPENAI_API_KEY_HERE":
                        text_api_key = OPENAI_API_KEY
                
                elif text_provider == "text_ru" and text_api_key is None:
                    if TEXT_RU_API_KEY and TEXT_RU_API_KEY != "YOUR_TEXT_RU_API_KEY_HERE":
                        text_api_key = TEXT_RU_API_KEY
                
                if image_provider == "openai" and image_api_key is None:
                    if OPENAI_API_KEY and OPENAI_API_KEY != "YOUR_OPENAI_API_KEY_HERE":
                        image_api_key = OPENAI_API_KEY
                
                elif image_provider == "stability" and image_api_key is None:
                    if STABILITY_API_KEY and STABILITY_API_KEY != "YOUR_STABILITY_API_KEY_HERE":
                        image_api_key = STABILITY_API_KEY
                        
            except ImportError:
                pass
        
        # Initialize text rewriter
        if text_provider == "openai" and text_api_key:
            self.text_rewriter = OpenAIRewriter(text_api_key)
        elif text_provider == "text_ru" and text_api_key:
            self.text_rewriter = TextRuRewriter(text_api_key)
        else:
            self.text_rewriter = None
            logger.warning("No valid text rewriting API configured")
        
        # Initialize image generator
        if image_api_key:
            self.image_generator = ImageGenerator(image_api_key, image_provider)
        else:
            self.image_generator = None
            logger.warning("No valid image generation API configured")
    
    async def process_news(self, news_item: NewsItem, 
                          rewrite: bool = True, 
                          generate_image: bool = True) -> Tuple[Optional[str], Optional[str]]:
        """
        Process a single news item
        
        Returns: (rewritten_text, image_url_or_path)
        """
        
        rewritten_text = None
        image_result = None
        
        # Rewrite text
        if rewrite and self.text_rewriter:
            full_text = f"{news_item.title}\n\n{news_item.content}"
            rewritten_text = await self.text_rewriter.rewrite_text(full_text)
            
            if rewritten_text:
                logger.info(f"Successfully rewrote news: {news_item.title[:50]}...")
            else:
                logger.warning(f"Failed to rewrite news: {news_item.title[:50]}...")
                rewritten_text = full_text
        
        # Generate image
        if generate_image and self.image_generator:
            # Create prompt from news content
            image_prompt = f"{news_item.title}. Professional business news illustration, polymer industry, modern style"
            
            image_result = await self.image_generator.generate_image(
                image_prompt, 
                news_item.title
            )
            
            if image_result:
                logger.info(f"Generated image for news: {news_item.title[:50]}...")
        
        return rewritten_text, image_result
    
    async def process_multiple_news(self, news_items: List[NewsItem],
                                   selected_indices: List[int]) -> dict:
        """
        Process multiple selected news items
        
        Args:
            news_items: List of all collected news
            selected_indices: Indices of news items to process
        
        Returns: Dictionary with processed results
        """
        
        results = {}
        
        for idx in selected_indices:
            if 0 <= idx < len(news_items):
                news_item = news_items[idx]
                logger.info(f"Processing news #{idx + 1}: {news_item.title[:50]}...")
                
                rewritten_text, image_result = await self.process_news(
                    news_item,
                    rewrite=True,
                    generate_image=True
                )
                
                results[idx] = {
                    "original": news_item,
                    "rewritten_text": rewritten_text,
                    "image": image_result
                }
        
        return results
