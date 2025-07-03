"""
🚀 图像处理性能优化模块
专门用于优化图像上传、处理和显示的速度
"""

import cv2
import numpy as np
import streamlit as st
import hashlib
import time
from pathlib import Path
import tempfile
from PIL import Image, ImageEnhance
from functools import lru_cache
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import io

class ImageProcessor:
    """优化的图像处理器"""
    
    def __init__(self, max_workers=2):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.cache = {}
        self.max_cache_size = 100
        self.processing_times = []
        
    def get_image_hash(self, image_data):
        """生成图像数据的哈希值"""
        if isinstance(image_data, bytes):
            return hashlib.md5(image_data).hexdigest()[:16]
        elif hasattr(image_data, 'read'):
            pos = image_data.tell()
            image_data.seek(0)
            hash_val = hashlib.md5(image_data.read()).hexdigest()[:16]
            image_data.seek(pos)
            return hash_val
        return None
    
    def manage_cache(self):
        """管理缓存大小"""
        if len(self.cache) > self.max_cache_size:
            # 删除最旧的条目
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
    
    @lru_cache(maxsize=50)
    def cached_resize(self, image_shape, target_width, target_height):
        """缓存调整大小的计算"""
        h, w = image_shape[:2]
        if w == target_width and h == target_height:
            return None  # 不需要调整
        return (target_width, target_height)
    
    def fast_decode_image(self, image_data):
        """快速解码图像"""
        start_time = time.time()
        
        # 检查缓存
        cache_key = self.get_image_hash(image_data)
        if cache_key and cache_key in self.cache:
            st.session_state['performance_metrics']['cache_hits'] += 1
            return self.cache[cache_key].copy()
        
        st.session_state['performance_metrics']['cache_misses'] += 1
        
        try:
            # 使用PIL进行更快的解码
            if isinstance(image_data, bytes):
                image = Image.open(io.BytesIO(image_data))
            else:
                image = Image.open(image_data)
            
            # 转换为OpenCV格式
            image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # 缓存结果
            if cache_key:
                self.manage_cache()
                self.cache[cache_key] = image_cv.copy()
            
            processing_time = time.time() - start_time
            self.processing_times.append(processing_time)
            
            return image_cv
            
        except Exception as e:
            st.error(f"图像解码失败: {str(e)}")
            return None
    
    def smart_resize(self, image, target_width=640, target_height=480, maintain_aspect=True):
        """智能调整图像大小"""
        if image is None:
            return None
            
        h, w = image.shape[:2]
        
        # 如果已经是目标尺寸，直接返回
        if w == target_width and h == target_height:
            return image
        
        if maintain_aspect:
            # 保持宽高比
            aspect_ratio = w / h
            target_aspect = target_width / target_height
            
            if aspect_ratio > target_aspect:
                new_width = target_width
                new_height = int(target_width / aspect_ratio)
            else:
                new_height = target_height
                new_width = int(target_height * aspect_ratio)
        else:
            new_width, new_height = target_width, target_height
        
        # 使用更快的插值方法
        if w * h > target_width * target_height:
            interpolation = cv2.INTER_AREA  # 缩小时使用
        else:
            interpolation = cv2.INTER_LINEAR  # 放大时使用
        
        return cv2.resize(image, (new_width, new_height), interpolation=interpolation)
    
    def batch_process_images(self, uploaded_files, progress_callback=None):
        """批量处理图像"""
        if not uploaded_files:
            return []
        
        def process_single(file_data):
            file_obj, index = file_data
            try:
                # 读取文件数据
                if hasattr(file_obj, 'read'):
                    file_obj.seek(0)
                    image_data = file_obj.read()
                    file_obj.seek(0)
                else:
                    image_data = file_obj
                
                # 解码图像
                image = self.fast_decode_image(image_data)
                if image is None:
                    return None
                
                # 调整大小
                resized = self.smart_resize(image, 640, 480)
                
                return {
                    'index': index,
                    'original': image,
                    'resized': resized,
                    'name': getattr(file_obj, 'name', f'image_{index}'),
                    'status': 'success'
                }
                
            except Exception as e:
                return {
                    'index': index,
                    'error': str(e),
                    'name': getattr(file_obj, 'name', f'image_{index}'),
                    'status': 'error'
                }
        
        # 并行处理
        file_data = [(f, i) for i, f in enumerate(uploaded_files)]
        
        if len(uploaded_files) > 1:
            # 多文件并行处理
            futures = []
            for data in file_data:
                future = self.executor.submit(process_single, data)
                futures.append(future)
            
            results = []
            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                if result:
                    results.append(result)
                
                # 更新进度
                if progress_callback:
                    progress_callback(i + 1, len(futures))
            
            # 按索引排序
            results.sort(key=lambda x: x.get('index', 0))
            return results
        else:
            # 单文件处理
            result = process_single(file_data[0])
            return [result] if result else []
    
    def optimize_for_display(self, image, max_width=800, max_height=600):
        """优化图像用于显示"""
        if image is None:
            return None
        
        # 如果图像太大，先缩小
        h, w = image.shape[:2]
        if w > max_width or h > max_height:
            image = self.smart_resize(image, max_width, max_height, maintain_aspect=True)
        
        # 优化图像质量（减少噪声，提高对比度）
        if len(image.shape) == 3:
            # 轻微的高斯模糊去噪
            image = cv2.GaussianBlur(image, (3, 3), 0)
            
            # 调整对比度和亮度
            alpha = 1.1  # 对比度
            beta = 5     # 亮度
            image = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
        
        return image
    
    def create_thumbnail(self, image, size=(200, 150)):
        """创建缩略图"""
        if image is None:
            return None
        
        return self.smart_resize(image, size[0], size[1], maintain_aspect=True)
    
    def get_processing_stats(self):
        """获取处理统计信息"""
        if not self.processing_times:
            return {"avg_time": 0, "total_processed": 0}
        
        return {
            "avg_time": sum(self.processing_times) / len(self.processing_times),
            "total_processed": len(self.processing_times),
            "cache_size": len(self.cache)
        }

class StreamlitImageOptimizer:
    """Streamlit 图像显示优化器"""
    
    def __init__(self):
        self.processor = ImageProcessor()
        
    def display_image_with_cache(self, image, caption="", channels="BGR", key=None):
        """缓存优化的图像显示"""
        if image is None:
            return
        
        # 生成显示键
        display_key = f"display_{key}_{caption}" if key else f"display_{caption}"
        
        # 检查是否需要更新显示
        if display_key in st.session_state.get('display_cache', {}):
            cached_image = st.session_state['display_cache'][display_key]
            if np.array_equal(cached_image, image):
                return  # 图像没有变化，不需要重新显示
        
        # 优化图像用于显示
        optimized_image = self.processor.optimize_for_display(image)
        
        # 显示图像
        st.image(optimized_image, caption=caption, channels=channels)
        
        # 缓存显示的图像
        if 'display_cache' not in st.session_state:
            st.session_state['display_cache'] = {}
        st.session_state['display_cache'][display_key] = optimized_image.copy()
    
    def create_image_grid(self, images, captions=None, cols=3):
        """创建图像网格显示"""
        if not images:
            return
        
        num_images = len(images)
        rows = (num_images + cols - 1) // cols
        
        for row in range(rows):
            columns = st.columns(cols)
            for col in range(cols):
                idx = row * cols + col
                if idx < num_images:
                    with columns[col]:
                        caption = captions[idx] if captions and idx < len(captions) else f"图像 {idx + 1}"
                        thumbnail = self.processor.create_thumbnail(images[idx])
                        if thumbnail is not None:
                            st.image(thumbnail, caption=caption, channels="BGR")
    
    def progress_image_processing(self, uploaded_files, processing_func):
        """带进度条的图像处理"""
        if not uploaded_files:
            return []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(current, total):
            progress = current / total
            progress_bar.progress(progress)
            status_text.text(f"处理进度: {current}/{total} ({progress:.1%})")
        
        try:
            results = self.processor.batch_process_images(
                uploaded_files, 
                progress_callback=update_progress
            )
            
            # 清理进度显示
            progress_bar.empty()
            status_text.empty()
            
            return results
            
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"处理过程中出现错误: {str(e)}")
            return []

# 全局实例
_image_optimizer = None

def get_image_optimizer():
    """获取全局图像优化器实例"""
    global _image_optimizer
    if _image_optimizer is None:
        _image_optimizer = StreamlitImageOptimizer()
    return _image_optimizer

def optimize_image_display(image, caption="", channels="BGR", key=None):
    """优化图像显示的便捷函数"""
    optimizer = get_image_optimizer()
    optimizer.display_image_with_cache(image, caption, channels, key)

def process_uploaded_images(uploaded_files):
    """处理上传图像的便捷函数"""
    optimizer = get_image_optimizer()
    return optimizer.progress_image_processing(uploaded_files, None)
