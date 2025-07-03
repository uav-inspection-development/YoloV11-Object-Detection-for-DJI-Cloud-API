"""
🚀 Streamlit 性能优化配置文件
提高图片上传、处理和切换的速度
"""

import streamlit as st
import os
import tempfile
from pathlib import Path


def optimize_streamlit_performance():
    """配置 Streamlit 性能优化选项"""
    
    # 优化 Session State 管理
    if 'performance_optimized' not in st.session_state:
        # 初始化性能相关的 session state
        st.session_state['performance_optimized'] = True
        st.session_state['image_cache'] = {}
        st.session_state['processing_cache'] = {}
        st.session_state['display_cache'] = {}
        
        # 清理可能的内存泄漏
        cleanup_session_state()

def cleanup_session_state():
    """清理 Session State 中不必要的数据"""
    keys_to_remove = []
    for key in st.session_state.keys():
        if key.startswith('temp_') or key.startswith('old_'):
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del st.session_state[key]

def setup_image_optimization():
    """设置图像优化相关配置"""
    
    # 创建临时目录用于图像缓存
    temp_dir = Path(tempfile.gettempdir()) / "yolo_streamlit_cache"
    temp_dir.mkdir(exist_ok=True)
    
    # 设置图像显示的最佳尺寸
    if 'display_settings' not in st.session_state:
        st.session_state['display_settings'] = {
            'max_image_width': 800,
            'max_image_height': 600,
            'thumbnail_size': (200, 150),
            'compression_quality': 85
        }
    
    return temp_dir

def add_performance_css():
    """添加CSS来优化界面性能"""
    st.markdown("""
    <style>
    /* 优化图片加载 */
    .stImage > img {
        transition: opacity 0.1s ease-in-out;
        image-rendering: -webkit-optimize-contrast;
        image-rendering: optimize-contrast;
    }
    
    /* 优化表格显示 */
    .stDataFrame {
        font-size: 12px;
        max-height: 400px;
        overflow-y: auto;
    }
    
    /* 减少动画延迟 */
    .stProgress .stProgress-bar {
        transition: width 0.1s ease;
    }
    
    /* 优化按钮响应 */
    .stButton > button {
        transition: all 0.1s ease;
    }
    
    /* 隐藏不必要的元素 */
    .stDeployButton {
        display: none;
    }
    
    /* 优化侧边栏 */
    .css-1d391kg {
        padding-top: 1rem;
    }
    
    /* 预加载图像 */
    .image-container {
        position: relative;
        overflow: hidden;
    }
    
    .image-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, 
            rgba(240,240,240,0.3) 25%, 
            rgba(250,250,250,0.5) 50%, 
            rgba(240,240,240,0.3) 75%);
        animation: shimmer 1.5s infinite;
        z-index: 1;
    }
    
    @keyframes shimmer {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }
    
    /* 优化文件上传器 */
    .stFileUploader label {
        font-size: 14px;
    }
    
    .stFileUploader [data-testid="stFileUploaderDropzone"] {
        min-height: 100px;
    }
    </style>
    """, unsafe_allow_html=True)

def optimize_file_upload():
    """优化文件上传配置"""
    # 设置文件上传的最大大小和类型限制
    upload_config = {
        'max_file_size': 50,  # MB
        'allowed_types': ['jpg', 'jpeg', 'png', 'bmp', 'tiff'],
        'max_files': 20,
        'chunk_size': 1024 * 1024  # 1MB chunks
    }
    
    if 'upload_config' not in st.session_state:
        st.session_state['upload_config'] = upload_config
    
    return upload_config

def create_performance_monitor():
    """创建性能监控组件"""
    if 'performance_metrics' not in st.session_state:
        st.session_state['performance_metrics'] = {
            'images_processed': 0,
            'total_processing_time': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    # 在侧边栏显示性能指标
    with st.sidebar:
        with st.expander("🔧 性能监控", expanded=False):
            metrics = st.session_state['performance_metrics']
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("图片处理", metrics['images_processed'])
                st.metric("缓存命中", metrics['cache_hits'])
            
            with col2:
                avg_time = (metrics['total_processing_time'] / max(metrics['images_processed'], 1))
                st.metric("平均用时", f"{avg_time:.2f}s")
                st.metric("缓存未命中", metrics['cache_misses'])
            
            if st.button("重置统计"):
                st.session_state['performance_metrics'] = {
                    'images_processed': 0,
                    'total_processing_time': 0,
                    'cache_hits': 0,
                    'cache_misses': 0
                }
                st.rerun()

def add_loading_spinner():
    """添加加载动画"""
    return st.spinner('🚀 正在处理中...')

def show_performance_tips():
    """显示性能优化提示"""
    with st.sidebar:
        with st.expander("💡 性能优化提示", expanded=False):
            st.markdown("""
            **提高处理速度的建议：**
            
            1. 📏 **图像尺寸**: 建议上传尺寸小于2000x2000像素的图片
            2. 📁 **文件格式**: JPEG格式处理速度最快
            3. 🔄 **批量处理**: 一次上传多张图片比逐个上传更高效
            4. 💾 **缓存使用**: 重复处理相同图片会自动使用缓存
            5. 🎯 **目标过滤**: 使用目标过滤功能可以减少渲染开销
            6. 🖥️ **浏览器**: 建议使用Chrome或Edge浏览器
            7. 🌐 **网络**: 确保网络连接稳定，避免上传中断
            """)
