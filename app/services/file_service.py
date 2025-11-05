import os
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import UploadFile, HTTPException
from PIL import Image, ImageOps
import io
import mimetypes

from app.core.config import settings


class FileService:
    """Service for handling file uploads and management"""
    
    def __init__(self):
        self.upload_dir = Path("app/static/uploads")
        self.product_images_dir = self.upload_dir / "products"
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure upload directories exist"""
        self.upload_dir.mkdir(exist_ok=True)
        self.product_images_dir.mkdir(exist_ok=True)
    
    async def upload_product_image(self, file: UploadFile, product_id: str) -> str:
        """Upload and process a product image"""
        try:
            # Validate file type
            if not file.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="File must be an image")
            
            # Validate file size (max 10MB)
            if file.size and file.size > 10 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="File size must be less than 10MB")
            
            # Read and validate image
            content = await file.read()
            try:
                image = Image.open(io.BytesIO(content))
                # Convert to RGB if necessary
                if image.mode in ('RGBA', 'LA', 'P'):
                    image = image.convert('RGB')
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid image file")
            
            # Generate unique filename
            file_extension = self._get_file_extension(file.filename)
            filename = f"{product_id}_{uuid.uuid4().hex[:8]}{file_extension}"
            file_path = self.product_images_dir / filename
            
            # Save image with optimization
            image.save(file_path, 'JPEG', quality=85, optimize=True)
            
            # Return the URL path
            return f"/static/uploads/products/{filename}"
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")
    
    def delete_product_image(self, image_url: str) -> bool:
        """Delete a product image and its thumbnail"""
        try:
            if not image_url or not image_url.startswith('/static/uploads/products/'):
                return False
            
            # Extract filename from URL
            filename = image_url.split('/')[-1]
            file_path = self.product_images_dir / filename
            
            # Delete main image
            if file_path.exists():
                file_path.unlink()
            
            # Delete thumbnail if it exists
            name_without_ext = Path(filename).stem
            thumbnail_filename = f"{name_without_ext}_thumb.jpg"
            thumbnail_path = self.product_images_dir / thumbnail_filename
            
            if thumbnail_path.exists():
                thumbnail_path.unlink()
            
            return True
            
        except Exception:
            return False
    
    def _get_file_extension(self, filename: str) -> str:
        """Get file extension from filename"""
        if not filename:
            return '.jpg'
        
        # Get the original extension
        ext = Path(filename).suffix.lower()
        
        # Map common image extensions to .jpg
        image_extensions = {'.png', '.gif', '.bmp', '.tiff', '.webp'}
        if ext in image_extensions:
            return '.jpg'
        
        return ext if ext in {'.jpg', '.jpeg'} else '.jpg'
    
    def get_image_info(self, image_url: str) -> Optional[Dict[str, Any]]:
        """Get information about an uploaded image"""
        try:
            if not image_url or not image_url.startswith('/static/uploads/products/'):
                return None
            
            filename = image_url.split('/')[-1]
            file_path = self.product_images_dir / filename
            
            if not file_path.exists():
                return None
            
            # Get file stats
            stat = file_path.stat()
            
            # Get image dimensions and format
            with Image.open(file_path) as img:
                width, height = img.size
                format_name = img.format or 'JPEG'
                mode = img.mode
            
            return {
                'filename': filename,
                'size': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'width': width,
                'height': height,
                'format': format_name,
                'mode': mode,
                'created': stat.st_ctime,
                'modified': stat.st_mtime,
                'aspect_ratio': round(width / height, 2) if height > 0 else 0
            }
            
        except Exception:
            return None
    
    def resize_image(self, image_url: str, max_width: int = 800, max_height: int = 600) -> bool:
        """Resize an image to fit within specified dimensions"""
        try:
            if not image_url or not image_url.startswith('/static/uploads/products/'):
                return False
            
            filename = image_url.split('/')[-1]
            file_path = self.product_images_dir / filename
            
            if not file_path.exists():
                return False
            
            with Image.open(file_path) as img:
                # Calculate new dimensions
                width, height = img.size
                
                if width <= max_width and height <= max_height:
                    return True  # No resize needed
                
                # Calculate new dimensions maintaining aspect ratio
                ratio = min(max_width / width, max_height / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                
                # Resize image
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Save resized image
                resized_img.save(file_path, 'JPEG', quality=85, optimize=True)
                
                return True
                
        except Exception:
            return False
    
    def create_thumbnail(self, image_url: str, size: tuple = (150, 150)) -> Optional[str]:
        """Create a thumbnail version of an image"""
        try:
            if not image_url or not image_url.startswith('/static/uploads/products/'):
                return None
            
            filename = image_url.split('/')[-1]
            file_path = self.product_images_dir / filename
            
            if not file_path.exists():
                return None
            
            # Generate thumbnail filename
            name_without_ext = Path(filename).stem
            thumbnail_filename = f"{name_without_ext}_thumb.jpg"
            thumbnail_path = self.product_images_dir / thumbnail_filename
            
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Create thumbnail
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # Save thumbnail
                img.save(thumbnail_path, 'JPEG', quality=85, optimize=True)
                
                return f"/static/uploads/products/{thumbnail_filename}"
                
        except Exception:
            return None
    
    def optimize_image(self, image_url: str, quality: int = 85) -> bool:
        """Optimize an image for web use"""
        try:
            if not image_url or not image_url.startswith('/static/uploads/products/'):
                return False
            
            filename = image_url.split('/')[-1]
            file_path = self.product_images_dir / filename
            
            if not file_path.exists():
                return False
            
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Save optimized image
                img.save(file_path, 'JPEG', quality=quality, optimize=True)
                
                return True
                
        except Exception:
            return False
    
    def add_watermark(self, image_url: str, watermark_text: str = "CNPERP") -> bool:
        """Add a watermark to an image"""
        try:
            if not image_url or not image_url.startswith('/static/uploads/products/'):
                return False
            
            filename = image_url.split('/')[-1]
            file_path = self.product_images_dir / filename
            
            if not file_path.exists():
                return False
            
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Create a copy for watermarking
                watermarked = img.copy()
                
                # Add watermark (simple text overlay)
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(watermarked)
                
                # Use default font
                try:
                    font = ImageFont.truetype("arial.ttf", 24)
                except:
                    font = ImageFont.load_default()
                
                # Calculate text position (bottom right corner)
                bbox = draw.textbbox((0, 0), watermark_text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                x = img.width - text_width - 10
                y = img.height - text_height - 10
                
                # Draw text with semi-transparent background
                draw.rectangle([x-5, y-5, x+text_width+5, y+text_height+5], 
                             fill=(0, 0, 0, 128))
                draw.text((x, y), watermark_text, fill=(255, 255, 255), font=font)
                
                # Save watermarked image
                watermarked.save(file_path, 'JPEG', quality=85, optimize=True)
                
                return True
                
        except Exception:
            return False
    
    def get_image_statistics(self) -> Dict[str, Any]:
        """Get statistics about uploaded images"""
        try:
            total_files = 0
            total_size = 0
            formats = {}
            
            for file_path in self.product_images_dir.glob('*'):
                if file_path.is_file():
                    total_files += 1
                    total_size += file_path.stat().st_size
                    
                    # Count formats
                    ext = file_path.suffix.lower()
                    formats[ext] = formats.get(ext, 0) + 1
            
            return {
                'total_files': total_files,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'formats': formats,
                'directory': str(self.product_images_dir)
            }
            
        except Exception:
            return {}
