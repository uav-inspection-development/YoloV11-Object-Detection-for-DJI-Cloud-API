# -*- coding: utf-8 -*-
"""
文件命名和标签配置模块
用于统一管理系统中的中文命名规则和标签映射
"""

# 图像类型中文名称映射
IMAGE_TYPE_MAP = {
    "EL": "电致发光",
    "可见光": "可见光",
    "红外": "红外热成像", 
    "Thermo": "红外热成像",
    "Visible": "可见光",
    "热红外": "红外热成像",
    "thermal": "红外热成像",
    "visible": "可见光",
    "el": "电致发光"
}

# 任务类型中文名称映射
TASK_TYPE_MAP = {
    "检测任务": "缺陷检测",
    "分割任务": "区域分割",
    "Detection": "缺陷检测",
    "Segmentation": "区域分割",
    "detection": "缺陷检测",
    "segmentation": "区域分割",
    "detect": "缺陷检测",
    "segment": "区域分割"
}

# 导出格式中文描述
EXPORT_FORMAT_MAP = {
    "CSV": "CSV数据表",
    "Excel": "Excel电子表格",
    "JSON": "JSON数据文件",
    "Word": "Word检测报告"
}

# 检测结果状态中文描述
DETECTION_STATUS_MAP = {
    "success": "检测完成",
    "failed": "检测失败",
    "processing": "正在检测",
    "pending": "等待检测"
}

# 文件命名模板
FILENAME_TEMPLATES = {
    "report": "光伏板{task_type}报告-{image_type}-{timestamp}",
    "data": "光伏板检测数据-{image_type}-{timestamp}",
    "log": "检测日志-{timestamp}",
    "image": "检测结果图-{image_type}-{timestamp}"
}

def get_image_type_name(image_type):
    """获取图像类型的中文名称"""
    return IMAGE_TYPE_MAP.get(image_type, image_type)

def get_task_type_name(task_type):
    """获取任务类型的中文名称"""
    return TASK_TYPE_MAP.get(task_type, task_type)

def get_export_format_name(export_format):
    """获取导出格式的中文描述"""
    return EXPORT_FORMAT_MAP.get(export_format, export_format)

def generate_filename(template_type, **kwargs):
    """
    根据模板生成文件名
    
    Args:
        template_type: 模板类型 ('report', 'data', 'log', 'image')
        **kwargs: 模板参数，如 image_type, task_type, timestamp 等
    
    Returns:
        生成的文件名（不包含扩展名）
    """
    template = FILENAME_TEMPLATES.get(template_type, FILENAME_TEMPLATES["data"])
    
    # 处理参数映射
    processed_kwargs = {}
    for key, value in kwargs.items():
        if key == 'image_type':
            processed_kwargs[key] = get_image_type_name(value)
        elif key == 'task_type':
            processed_kwargs[key] = get_task_type_name(value)
        else:
            processed_kwargs[key] = value
    
    try:
        return template.format(**processed_kwargs)
    except KeyError as e:
        # 如果缺少必要参数，返回默认格式
        return f"光伏板检测文件-{kwargs.get('timestamp', 'unknown')}"

# 侧边栏标签优化
SIDEBAR_LABELS = {
    "settings_menu": "🔧 设置菜单",
    "login_settings": "🔒 登陆设置",
    "logout_button": "🚪 退出登陆",
    "display_settings": "🖥️ 显示设置",
    "log_path_settings": "📂 日志保存路径设置",
    "export_format_settings": "📤 日志导出格式设置",
    "detection_thresholds": "⚙️ 检测阈值设定",
    "model_settings": "🧠 模型设置",
    "image_type_selection": "🖼️ 图像类型选择",
    "target_class_selection": "🎯 目标类别选择",
    "model_file_settings": "📁 模型文件设置",
    "input_source_settings": "📹 输入源识别设置",
    "image_preview": "🖼️ 图像预览",
    "detection_params": "⚙️ 检测参数",
    "export_options": "📤 导出选项",
    "history": "📜 历史记录",
    "statistics": "📊 统计信息",
    "about": "📖 关于"
}

# 按钮文本优化
BUTTON_TEXTS = {
    "start_detection": "🚀 开始检测",
    "stop_detection": "⏹️ 停止检测",
    "export_results": "📤 导出结果",
    "clear_results": "🗑️ 清空结果",
    "previous_image": "⬅️ 上一张",
    "next_image": "下一张 ➡️",
    "sidebar_prev": "⬅️",
    "sidebar_next": "➡️",
    "prev_btn": "⬅️ 上一张",
    "next_btn": "下一张 ➡️",
    "stop": "停止"
}

# 系统设置和配置
SYSTEM_CONFIG = {
    "title": "光伏云组件检测系统",
    "model_type_detection": "检测任务",
    "model_type_segmentation": "分割任务",
    "image_type_visible": "可见光",
    "image_type_thermal": "红外",
    "image_type_el": "EL隐裂",
    "image_enhancement_none": "不处理",
    "undistortion_none": "不去除",
    "undistortion_camera_calc": "相机参数计算",
    "undistortion_manual": "手动调整参数",
    "target_all": "全部目标"
}

# 界面选项配置
UI_OPTIONS = {
    "aspect_ratios": ["16:9", "4:3", "自由调整"],
    "export_formats": ["Word", "CSV", "Excel", "JSON"],
    "task_types": ["检测任务", "分割任务"],
    "model_settings": ["默认", "指定权重文件"],
    "input_sources": ["图片文件", "图片文件夹", "视频文件", "视频文件夹", "摄像头", "RTSP/RTMP流"],
    "image_enhancement_methods": ["不处理", "CLAHE", "Histogram Equalization"],
    "undistortion_methods": ["不去除", "相机参数计算", "手动调整参数"],
    "display_modes": ["叠加显示", "对比显示"]
}

# 界面选择器标签
UI_SELECTORS = {
    "aspect_ratio_selection": "选择显示比例",
    "export_format_selection": "选择导出格式",
    "task_type_selection": "选择任务类型",
    "model_settings": "模型设置",
    "input_source_selection": "选择输入源",
    "camera_selection": "选择摄像头序号",
    "display_mode_selection": "单/双画面显示"
}

# 界面提示文本
UI_LABELS = {
    "aspect_ratio_selection": "选择显示比例",
    "display_height_input": "输入显示高度 (默认: 1080)",
    "display_width_input": "输入显示宽度",
    "display_width_input_free": "输入显示宽度 (默认: 1080)",
    "display_height_input_free": "输入显示高度 (默认: 720)",
    "csv_output_path_input": "修改日志输出路径 (默认路径为output/logs/)",
    "export_format_selection": "选择导出格式",
    "export_format_hint": "💡 提示: {format} 文件将导出至 {path} 路径。",
    "conf_threshold_slider": "置信度设定",
    "conf_threshold_hint": "💡 提示: 置信度设定范围为0.0到1.0，代表检测结果的置信度。",
    "iou_threshold_slider": "IOU设定",
    "iou_threshold_hint": "💡 提示: IOU设定范围为0.0到1.0，代表检测结果的重叠度。",
    "task_type_selection": "选择任务类型",
    "detection_task_hint": "💡 提示: 检测任务将检测异常的光伏板组件或其他异常，目标类别按实际需要选择。",
    "segmentation_task_hint": "💡 提示: 分割任务将对所有的光伏板轮廓进行分割，选择输出矩形边框后，将检测矩形边框并输出，否则输出原始边缘，目标类别选择【单组件】或【组串】即可。",
    "rectangle_output_checkbox": "输出矩形边框",
    "image_type_hint": "💡 提示: 当前选择的图像类型为: {type}",
    "target_class_multiselect": "选择检测目标类别",
    "no_class_selected_hint": "💡 提示: 未选择任何类别，模型将不会检测任何目标。",
    "selected_classes_hint": "💡 提示: 当前选择的类别为: {classes}",
    "model_file_radio": "模型设置",
    "upload_model_file": "选择.pt文件",
    "input_source_radio": "选择输入源",
    "camera_selection": "选择摄像头序号",
    "camera_hint": "💡 提示: 请点击'开始检测'按钮，启动摄像头检测！",
    "rtsp_input": "输入RTSP/RTMP地址",
    "rtsp_hint": "💡 提示: 请点击'开始检测'按钮，启动RTSP/RTMP流检测！",
    "upload_images": "上传图片",
    "upload_videos": "上传视频",
    "select_folder": "选择文件夹",
    "target_filter": "目标过滤",
    "current_config": "当前配置",
    "class_settings": "类别设置",
    "real_time_detection": "实时检测信息",
    "color_settings": "颜色设置",
    "session_state_data": "Session State 图像数据",
    "logtable_data": "LogTable 图像数据",
    "image_browser_control": "📸 图片浏览控制",
    "realtime_dashboard": "📊 实时监控仪表盘",
    "video_image_detection_system": "📷 视频/图片检测系统",
    "current_image_results": "🖼️ 当前图片检测结果",
    "history_log": "📜 历史日志",
    "all_targets": "全部目标",
    "image_preprocessing_preview": "🖼️ 图片预处理预览",
    # 视频显示画面标签
    "camera_detection_view": "摄像头识别画面",
    "camera_original_view": "摄像头原始画面", 
    "rtsp_detection_view": "RTSP识别画面",
    "rtsp_original_view": "RTSP原始画面",
    # 图像处理提示
    "false_color_hint": "💡 提示: 伪彩色转换针对于输入图像为黑白图像且图像类型为红外热图。",
    "rotation_correction_hint": "💡 提示: 图像旋转校正用于修正图像的倾斜角度，适用于拍摄角度不正的图像。",
    "perspective_correction_hint": "💡 提示: 梯形校正用于修正图像的透视畸变，适用于拍摄角度不正的图像。目前仅适用于EL图像检测。",
    "image_enhancement_hint": "💡 提示: 图像增强可以改善图像的对比度和细节，使检测结果更加准确。",
    "camera_calibration_hint": "💡 提示: 相机参数计算需要用户输入相机标定文件，手动调整参数需要保证输入图像包含较为明显的线条用于修正畸变。",
    "distortion_coefficient_hint": "💡 提示: 畸变系数用于描述镜头的径向畸变。畸变系数大于0：桶形畸变，图像边缘向外扩展；畸变系数小于0：枕形畸变，图像边缘向内收缩。",
    "folder_selection_hint": "💡 提示: 选择或输入本地图片文件夹路径，自动递归查找所有图片。",
    "video_folder_selection_hint": "💡 提示: 选择或输入本地视频文件夹路径，自动递归查找所有视频。",
    "image_upload_hint": "💡 提示: 请选择图片并点击'开始检测'按钮，进行图片检测！",
    "video_upload_hint": "💡 提示: 请选择视频并点击'开始检测'按钮，进行视频检测！"
}

# 状态消息模板
STATUS_MESSAGES = {
    "no_detection_results": "⚠️ 暂无检测结果，请先上传图片并开始检测",
    "frame_id_out_of_range_warning": "⚠️ 警告: 选择的帧ID {frame_id} 超出范围！当前有 {total} 张图片。",
    "index_out_of_range_warning": "⚠️ 警告: 检测到的类别索引 {cls_id} 超出范围！使用默认颜色。",
    "export_success": "✅ {file_type}已成功导出：\n{filename}",
    "export_error": "❌ 导出失败：{error}",
    "detection_complete": "✅ 检测完成！共处理 {count} 张图像",
    "detection_error": "❌ 检测过程中出现错误：{error}",
    "no_results": "⚠️ 暂无检测结果，请先进行检测",
    "loading": "⏳ 正在处理，请稍候...",
    "color_warning": "⚠️ 警告: 颜色列表长度与模型类别不一致！将使用随机颜色填充。",
    "oauth_error": "❌ 错误: 无法获取ACCESS_TOKEN，请检查您的凭据和token端点。",
    "no_camera_found": "未找到可用的摄像头",
    "scanning_folder": "🔍 正在扫描文件夹...",
    "upload_files_first": "请先上传图片文件或选择图片文件夹！",
    "upload_videos_first": "请先上传视频文件或选择视频文件夹！",
    "select_camera_first": "请先选择摄像头！",
    "input_rtsp_first": "请先输入RTSP/RTMP地址！",
    "unsupported_input_source": "不支持的输入源类型: {source}",
    "input_processing_error": "⚠️ 处理输入时发生错误: {error}",
    "model_load_error": "⚠️ 错误: 无法加载模型文件，请检查文件格式或路径是否正确！错误信息: {error}",
    "model_class_mismatch": "⚠️ 错误: 模型类别与选定类别不匹配，请检查模型文件或重新选择类别！",
    "unsupported_image_type": "⚠️ 错误: 不支持的图像类型！",
    "default_model_load_error": "⚠️ 错误: 无法加载默认模型文件，请检查文件路径或文件是否存在！错误信息: {error}",
    "model_class_auto_adjusted": "⚠️ 警告: 模型类别与选定类别已自动调整！",
    "no_detection_results": "暂无检测结果，请先上传图片并开始检测",
    "total_images_info": "共有 {count} 张检测结果图片",
    "image_index_info": "**第 {current} / {total} 张图片**",
    "filename_info": "文件名: {filename}",
    "image_slider_label": "选择图片",
    "current_frame_metric": "📸 当前帧数",
    "current_fps_metric": "⚡ 当前帧率 (FPS)",
    "target_count_metric": "🎯 检测目标数量",
    "detection_time_metric": "⏱️ 检测用时 (秒)",
    "image_detection_start": "🚀 开始图片检测...",
    "processing_files": "📋 准备处理 {count} 张图片...",
    "estimated_time": "⏱️ 预计总用时: {time:.1f} 秒",
    "processing_current": "🔄 正在处理: {filename} ({current}/{total})",
    "image_decode_error": "⚠️ 错误: 无法解码图像文件 {filename}，请检查文件格式是否正确！",
    "image_processing_error": "⚠️ 错误: 处理图像 {filename} 时发生错误：{error}",
    "batch_processing_complete": "🎉 批量检测完成！",
    "batch_processing_summary": "📊 处理完成: 成功 {successful_count} 张，失败 {failed_count} 张，总用时 {total_time:.2f} 秒",
    "batch_processing_progress": "✅ 已完成 {current}/{total} 张图片 | 预计剩余时间: {remaining_time:.1f} 秒",
    "single_image_processing_start": "🔄 开始处理单张图片...",
    "reading_image_file": "📁 正在读取图片文件...",
    "applying_image_processing": "🖼️ 正在应用图像处理...",
    "ai_detection_running": "🤖 正在进行AI检测...",
    "saving_detection_results": "💾 正在保存检测结果...",
    "updating_interface": "🔄 正在更新界面...",
    "image_decode_failed": "❌ 无法解码图片文件！",
    "single_image_detection_complete": "✅ 单张图片检测完成！检测到 {count} 个目标，用时 {time:.2f} 秒",
    "single_image_complete": "✅ 单张图片检测完成！",
    "image_detection_complete": "✅ 全部图片检测完成！",
    "single_image_processing_error": "❌ 处理单张图片时出错: {error}",
    # 视频处理相关
    "upload_video_first": "⚠️ 请先上传视频文件！",
    "video_processing_error": "❌ 处理视频时出错: {error}",
    "video_open_failed": "❌ 无法打开视频文件: {video_name}",
    "video_processing_start": "🔄 开始处理视频: {video_name} (总帧数: {total_frames})",
    "single_video_processing_error": "❌ 处理视频 {video_name} 时出错: {error}",
    # 摄像头处理相关
    "camera_open_failed": "❌ 无法打开摄像头 {camera_id}",
    "camera_started": "✅ 摄像头 {camera_id} 已启动，点击停止按钮结束检测",
    "camera_read_frame_failed": "❌ 无法从摄像头读取帧",
    "camera_processing_error": "❌ 处理摄像头输入时出错: {error}",
    # RTSP/RTMP处理相关
    "rtsp_connection_failed": "❌ 无法连接到RTSP/RTMP流: {rtsp_url}",
    "rtsp_connected": "✅ RTSP/RTMP流已连接: {rtsp_url}",
    "rtsp_stream_interrupted": "❌ RTSP/RTMP流中断，尝试重连...",
    "rtsp_processing_error": "❌ 处理RTSP/RTMP流时出错: {error}",
    # 系统信息和警告
    "git_info_not_found": "### 📊 版本信息\n未找到Git仓库信息",
    "unknown_version": "未知版本",
    "color_list_warning": "⚠️ 警告: 颜色列表长度与模型类别不一致！将使用随机颜色填充。",
    "no_camera_found": "未找到可用的摄像头",
    "more_files_remaining": "... 还有 {count} 个文件",
    "more_videos_remaining": "... 还有 {count} 个视频",
    "camera_calibration_success": "相机标定参数加载成功！",
    "camera_calibration_failed": "标定文件解析失败: {error}",
}

# 指标和仪表盘标签
METRICS_LABELS = {
    "current_frame": "📸 当前帧数",
    "current_fps": "⚡ 当前帧率 (FPS)",
    "target_count": "🎯 检测目标数量",
    "detection_time": "⏱️ 检测用时 (秒)",
    "total_files": "📊 总文件数",
    "file_size": "📊 总大小",
    "statistics_by_type": "按类型统计",
    "example_files": "示例文件",
    "total_size": "📊 总大小",
    "current_config": "### 当前配置",
    "model_type_label": "- 模型类型",
    "image_type_label": "- 图像类型", 
    "rectangle_output_label": "- 矩形框输出",
    "conf_threshold_label": "- 置信度阈值",
    "iou_threshold_label": "- IOU阈值",
    "class_settings": "### 类别设置",
    "available_classes_label": "- 可用类别(中文)",
    "selected_classes_label": "- 选择的类别(英文)",
    "model_classes_label": "- 模型类别"
}

def get_status_message(message_type, **kwargs):
    """获取格式化的状态消息"""
    template = STATUS_MESSAGES.get(message_type, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template

def get_metric_label(metric_type, **kwargs):
    """获取指标标签"""
    template = METRICS_LABELS.get(metric_type, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template
