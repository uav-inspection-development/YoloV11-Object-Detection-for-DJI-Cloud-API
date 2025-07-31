from collections import OrderedDict

from flask import Flask, request, jsonify, has_request_context
from flask_socketio import SocketIO, emit
import numpy as np
import cv2
import tempfile
import os
import sys
import base64
from web import Detection_UI
from license_features import DEFAULT_FEATURES
import threading
import json
from chinese_name_list import Visible_type, EL_type, Thermo_type, Segmentation_type, Other_type
from functools import wraps
import requests
from auth import verify_token, get_access_token
from naming_config import get_system_default, set_language, get_current_language


LICENSE_FEATURES = json.loads(
    os.getenv("LICENSE_FEATURES", json.dumps(DEFAULT_FEATURES))
)


# 初始化国际化支持
def init_api_language(lang_code=None):
    """
    初始化API服务的语言设置

    Args:
        lang_code: 语言代码 ('zh', 'en')，如果为None则使用系统默认
    """
    if lang_code is None:
        # 从环境变量或请求头获取语言设置，默认为中文
        lang_code = os.getenv("API_LANGUAGE", "zh")
    set_language(lang_code)
    return lang_code


# 获取本地化的系统默认值
def get_localized_values():
    """获取本地化的系统默认值"""
    return {
        'detection_task': get_system_default('model_type_detection'),
        'segmentation_task': get_system_default('model_type_segmentation'),
        'visible': get_system_default('image_type_visible'),
        'thermal': get_system_default('image_type_thermal'),
        'el_crack': get_system_default('image_type_el'),
        'other': get_system_default('image_type_other'),
        'undistortion_none': get_system_default('undistortion_none'),
        'undistortion_camera_calc': get_system_default('undistortion_camera_calc'),
        'undistortion_manual': get_system_default('undistortion_manual')
    }

# 初始化语言设置
init_api_language()


# 获取环境变量
# OAUTH2_INTROSPECT_URL = os.getenv("OAUTH2_INTROSPECT_URL")
# OAUTH2_TOKEN_URL = os.getenv("OAUTH2_TOKEN_URL")
# CLIENT_ID = os.getenv("CLIENT_ID")
# CLIENT_SECRET = os.getenv("CLIENT_SECRET")
#
# # 验证环境变量是否存在
# if not OAUTH2_INTROSPECT_URL or not CLIENT_ID or not CLIENT_SECRET:
#     sys.stderr.write(
#         "Error: Missing required environment variables.\n"
#         "Please set the following variables:\n"
#         "  - OAUTH2_INTROSPECT_URL\n"
#         "  - CLIENT_ID\n"
#         "  - CLIENT_SECRET\n"
#     )
#     sys.exit(1)

app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins='*')


@app.before_request
def detect_language():
    """
    自动检测请求中的语言设置
    支持以下方式设置语言：
    1. Accept-Language 请求头
    2. lang 查询参数
    3. X-Language 自定义请求头
    """
    if request.endpoint and not request.endpoint.startswith('static'):
        # 检查自定义请求头
        custom_lang = request.headers.get('X-Language')
        if custom_lang and custom_lang in ['zh', 'en']:
            set_language(custom_lang)
            return

        # 检查查询参数
        query_lang = request.args.get('lang')
        if query_lang and query_lang in ['zh', 'en']:
            set_language(query_lang)
            return

        # 检查 Accept-Language 请求头
        accept_language = request.headers.get('Accept-Language', '')
        if 'zh' in accept_language.lower():
            set_language('zh')
        elif 'en' in accept_language.lower():
            set_language('en')
        # 如果都没有匹配，保持当前语言设置


def require_oauth_token(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if has_request_context():
            auth = request.headers.get("Authorization", "")
            # if not auth.startswith("Bearer "):
            #     return jsonify({"error": "Missing or invalid Authorization header"}), 401
            # token = auth.split(" ")[1]
            # if not verify_token(token):
            #     return jsonify({"error": "Invalid or expired token"}), 403
        else:
            # WebSocket: 从 args[0] 中提取 token
            data = args[0] if args else {}
            token = data.get("access_token")
            # if not token or not verify_token(token):
            #     emit("stream_error", {"error": "Missing or invalid token"})
            #     return
        return func(*args, **kwargs)
    return wrapper

def validate_params(required_fields):
    """
    装饰器，用于验证请求参数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if has_request_context():  # HTTP / HTTPS 请求
                params = request.form.to_dict()
                files = request.files

                # selected_classes 处理
                if "selected_classes" in params and isinstance(params["selected_classes"], str):
                    try:
                        params["selected_classes"] = json.loads(params["selected_classes"])
                    except:
                        return jsonify({"error": "selected_classes must be a JSON array"}), 400

                # 参数校验 + 返回
                errors = _check_params(required_fields, params)
                if errors:
                    return jsonify({"error": "Invalid parameters", "details": errors}), 400

                # 注入 params 给函数
                return func(validated_params=params, files=files, *args, **kwargs)

            else:  # WebSocket 上下文
                data = args[0] if args else {}
                params = data.get("params", {})
                stream_source = data.get("stream_source", None)

                if not stream_source:
                    emit("stream_error", {"error": "Missing 'stream_source'"})
                    return

                if isinstance(params.get("selected_classes"), str):
                    try:
                        params["selected_classes"] = json.loads(params["selected_classes"])
                    except:
                        emit("stream_error", {"error": "selected_classes must be a JSON array"})
                        return

                errors = _check_params(required_fields, params)
                if errors:
                    emit("stream_error", {"error": "Invalid parameters", "details": errors})
                    return

                return func(params=params, stream_source=stream_source, *args[1:], **kwargs)

        return wrapper
    return decorator


def _check_params(required_fields, params):
    """
    通用参数检查逻辑
    """
    errors = []
    localized_values = get_localized_values()

    for key in required_fields:
        if key not in params:
            errors.append(f"Missing required parameter: '{key}'")

    try:
        if "conf_threshold" in params:
            val = float(params["conf_threshold"])
            if not 0 <= val <= 1:
                errors.append("conf_threshold must be between 0 and 1")
        if "iou_threshold" in params:
            val = float(params["iou_threshold"])
            if not 0 <= val <= 1:
                errors.append("iou_threshold must be between 0 and 1")
    except ValueError:
        errors.append("Threshold values must be float numbers")

    if "model_type" in params:
        valid_model_types = [localized_values['detection_task'], localized_values['segmentation_task']]
        if params["model_type"] not in valid_model_types:
            errors.append(f"model_type must be '{localized_values['detection_task']}' or '{localized_values['segmentation_task']}'")
        elif params["model_type"] not in LICENSE_FEATURES:
            errors.append(f"Feature '{params['model_type']}' not enabled")

    if "image_type" in params:
        valid_image_types = [
            localized_values['visible'],
            localized_values['thermal'],
            localized_values['el_crack'],
            localized_values['other']
        ]
        if params["image_type"] not in valid_image_types:
            valid_types_str = "', '".join(valid_image_types)
            errors.append(f"image_type must be one of ['{valid_types_str}']")
        elif params["image_type"] not in LICENSE_FEATURES and params["image_type"] != localized_values['other']:
            errors.append(f"Feature '{params['image_type']}' not enabled")

    if "selected_classes" in params and isinstance(params["selected_classes"], list):
        if not all(isinstance(cls, str) for cls in params["selected_classes"]):
            errors.append("All selected_classes must be strings")

        model_type = params.get("model_type", localized_values['detection_task'])
        image_type = params.get("image_type", localized_values['visible'])
        if model_type == localized_values['segmentation_task']:
            valid_classes = list(Segmentation_type.keys())
        elif image_type == localized_values['thermal']:
            valid_classes = list(Thermo_type.keys())
        elif image_type == localized_values['el_crack']:
            valid_classes = list(EL_type.keys())
        elif image_type == localized_values['visible']:
            valid_classes = list(Visible_type.keys())
        else:
            valid_classes = list(Other_type.keys())

        for cls in params["selected_classes"]:
            if cls not in valid_classes:
                errors.append(f"Invalid selected_class '{cls}' for image_type '{image_type}'")

    if "enable_pseudo_color" in params:
        if not (isinstance(params["enable_pseudo_color"], bool) or params["enable_pseudo_color"] in ["true", "false", "True", "False", 0, 1, "0", "1"]):
            errors.append("enable_pseudo_color must be a boolean or 'true'/'false'")

    if "undistortion_method" in params:
        valid_undistortion_methods = [
            localized_values['undistortion_none'],
            localized_values['undistortion_camera_calc'],
            localized_values['undistortion_manual']
        ]
        if params["undistortion_method"] not in valid_undistortion_methods:
            valid_methods_str = "', '".join(valid_undistortion_methods)
            errors.append(f"undistortion_method must be one of ['{valid_methods_str}']")

        # 如果选择了相机参数计算，必须提供 calibration_file
        if params["undistortion_method"] == localized_values['undistortion_camera_calc']:
            if "calibration_file" not in params or not params["calibration_file"]:
                errors.append(f"When undistortion_method is '{localized_values['undistortion_camera_calc']}', 'calibration_file' is required.")

    return errors


@app.route("/api/types", methods=["GET"])
@require_oauth_token
def get_types():
    """
    Retrieve solar panel types and tasks.

    Example Input:
    None (GET request)

    Example Output:
    {
        "Detection Task": {
            "Thermal": [
                {"name": "type1", "chinese_name": "类型1"},
                {"name": "type2", "chinese_name": "类型2"}
            ],
            "EL": [
                {"name": "type3", "chinese_name": "类型3"}
            ],
            "Visible": [
                {"name": "type4", "chinese_name": "类型4"}
            ],
            "Other": [
                {"name": "type8", "chinese_name": "类型5"}
            ]
        },
        "Segmentation Task": {
            "Thermal": [
                {"name": "type5", "chinese_name": "类型6"}
            ],
            "EL": [
                {"name": "type6", "chinese_name": "类型7"}
            ],
            "Visible": [
                {"name": "type7", "chinese_name": "类型8"}
            ]
        }
    }
    """
    try:
        localized_values = get_localized_values()

        tasks = {
            localized_values['detection_task']: {
                localized_values['thermal']: Thermo_type,
                localized_values['el_crack']: EL_type,
                localized_values['visible']: Visible_type,
                localized_values['other']: Other_type
            },
            localized_values['segmentation_task']: {
                localized_values['thermal']: Segmentation_type,
                localized_values['el_crack']: Segmentation_type,
                localized_values['visible']: Segmentation_type
            }
        }

        # Format the response
        response = {
            localized_values['detection_task']: {
                panel_type: [
                    {"name": name, "chinese_name": chinese_name}
                    for name, chinese_name in task.items()
                ]
                for panel_type, task in tasks[localized_values['detection_task']].items()
            },
            localized_values['segmentation_task']: {
                panel_type: [
                    {"name": name, "chinese_name": chinese_name}
                    for name, chinese_name in task.items()
                ]
                for panel_type, task in tasks[localized_values['segmentation_task']].items()
            }
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route("/api/language", methods=["POST"])
@require_oauth_token
def set_api_language():
    """
    Set the API language.

    Example Input:
    {
        "language": "en"  # or "zh"
    }

    Example Output:
    {
        "message": "Language set to English",
        "language": "en"
    }
    """
    try:
        data = request.get_json()
        if not data or "language" not in data:
            return jsonify({"error": "Missing 'language' parameter"}), 400

        lang_code = data["language"]
        if lang_code not in ["zh", "en"]:
            return jsonify({"error": "Language must be 'zh' or 'en'"}), 400

        set_language(lang_code)

        # Set environment variable for future requests
        os.environ["API_LANGUAGE"] = lang_code

        lang_name = "Chinese" if lang_code == "zh" else "English"
        return jsonify({
            "message": f"Language set to {lang_name}",
            "language": lang_code
        })

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route("/api/language", methods=["GET"])
@require_oauth_token
def get_api_language():
    """
    Get the current API language.

    Example Output:
    {
        "language": "zh",
        "language_name": "Chinese"
    }
    """
    try:
        current_lang = get_current_language()
        lang_name = "Chinese" if current_lang == "zh" else "English"

        return jsonify({
            "language": current_lang,
            "language_name": lang_name
        })

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route("/api/detect/image", methods=["POST"])
@require_oauth_token
@validate_params(["conf_threshold", "iou_threshold", "model_type", "image_type", "selected_classes", "enable_pseudo_color", "undistortion_method"])
def detect_image(validated_params, files):
    """
    Detect objects in an uploaded image.

    Example Input:
    Form-data:
    - image: (binary file) The image file to be processed.
    - conf_threshold: 0.5
    - iou_threshold: 0.4
    - model_type: "Detection Task" (or "检测任务" for Chinese)
    - image_type: "Visible" (or "可见光" for Chinese)
    - selected_classes: ["class1", "class2"]

    Example Output:
    {
        "detections": [
            ["class_name", [x1, y1, x2, y2], confidence, "time", class_id],
            ...
        ]
    }
    """
    try:
        det_info = []
        img_file = files.get("image")
        if not img_file:
            return jsonify({"error": "No image uploaded"}), 400

        img_data = np.frombuffer(img_file.read(), np.uint8)
        image = cv2.imdecode(img_data, cv2.IMREAD_COLOR)

        # 检查图片维度并处理
        original_shape = image.shape
        if len(image.shape) == 4 and image.shape[0] == 1:
            # 删除第一个维度（批量维度）
            image = image.squeeze(0)
            processed_shape = image.shape
        else:
            processed_shape = original_shape

        # 确保图片维度正确
        # if len(image.shape) != 3 or image.shape[0] != 3:
        #     return jsonify({
        #         "error": "Invalid image dimensions. Expected shape (3, 640, 640)",
        #         "original_shape": str(original_shape),
        #         "processed_shape": str(processed_shape)
        #     }), 400

        detector = Detection_UI(
            from_streamlit=False,
            api_params=validated_params,
            enabled_features=LICENSE_FEATURES,
        )
        _, det_info, _ = detector.frame_process(image, "api_image.jpg", is_api=True)
        transformed_list = []
        for item in det_info:
            transformed_item = OrderedDict([
                ("type", item[0]),
                ("name", item[1]),
                ("region", item[2]),
                ("area", item[3]),
                ("time", item[4]),
                ("class_id", item[5])
            ])
            transformed_list.append(transformed_item)
        return jsonify({"detections": transformed_list})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/detect/video", methods=["POST"])
@require_oauth_token
@validate_params(["conf_threshold", "iou_threshold", "model_type", "image_type", "selected_classes", "enable_pseudo_color", "undistortion_method"])
def detect_video(validated_params, files):
    """
    Detect objects in an uploaded video.

    Example Input:
    Form-data:
    - video: (binary file) The video file to be processed.
    - conf_threshold: 0.5
    - iou_threshold: 0.4
    - model_type: "Detection Task" (or "检测任务" for Chinese)
    - image_type: "Visible" (or "可见光" for Chinese)
    - selected_classes: ["class1", "class2"]

    Example Output:
    {
        "total_frames": 100,
        "results": [
            {
                "frame": 0,
                "detections": [
                    ["class_name", [x1, y1, x2, y2], confidence, "time", class_id],
                    ...
                ]
            },
            ...
        ]
    }
    """
    try:
        video_file = files.get("video")
        if not video_file:
            return jsonify({"error": "No video uploaded"}), 400

        tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tfile.write(video_file.read())
        tfile.close()

        cap = cv2.VideoCapture(tfile.name)
        detector = Detection_UI(
            from_streamlit=False,
            api_params=validated_params,
            enabled_features=LICENSE_FEATURES,
        )
        frame_results = []
        frame_id = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            _, det_info, _ = detector.frame_process(frame, f"frame_{frame_id}.jpg", is_api=True)
            transformed_list = []
            for item in det_info:
                transformed_item = OrderedDict([
                    ("type", item[0]),
                    ("name", item[1]),
                    ("region", item[2]),
                    ("area", item[3]),
                    ("time", item[4]),
                    ("class_id", item[5])
                ])
                transformed_list.append(transformed_item)
            if transformed_list:
                frame_results.append({
                    "frame": frame_id,
                    "detections": transformed_list
                })
            frame_id += 1

        cap.release()
        os.remove(tfile.name)

        return jsonify({
            "total_frames": frame_id,
            "results": frame_results
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@socketio.on('start_stream')
@require_oauth_token
# @validate_params(["conf_threshold", "iou_threshold", "model_type", "image_type", "selected_classes", "enable_pseudo_color", "undistortion_method"])
# FIXME:
def handle_stream(data):
    """
    Handle real-time video stream detection.

    Example Input:
    WebSocket message:
    {
        "params": {
            "conf_threshold": 0.5,
            "iou_threshold": 0.4,
            "model_type": "Detection Task" (or "检测任务" for Chinese),
            "image_type": "Visible" (or "可见光" for Chinese),
            "selected_classes": ["class1", "class2"]
        },
        "stream_source": "0"  # Camera index or RTSP/RTMP URL
    }

    Example Output:
    WebSocket message:
    {
        "detections": [
            ["class_name", [x1, y1, x2, y2], confidence, "time", class_id],
            ...
        ],
        "image": "<base64_encoded_image>"
    }
    """
    try:
        params = data.get("params", {})
        stream_source = data.get("stream_source", "0")

        if isinstance(stream_source, str) and stream_source.isdigit():
            stream_source = int(stream_source)

        cap = cv2.VideoCapture(stream_source)
        if not cap.isOpened():
            emit("stream_error", {"error": f"Unable to open stream: {stream_source}"})
            print(f"⚠️ 无法打开视频流: {stream_source}")
            return

        detector = Detection_UI(
            from_streamlit=False,
            api_params=params,
            enabled_features=LICENSE_FEATURES,
        )

        def stream_loop():
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret or frame is None:
                    print(f"⚠️ 无法读取视频帧或帧为空: {stream_source}")
                    emit("stream_warning", {"warning": "Failed to read video frame or frame is empty"})
                    continue

                _, det_info, _ = detector.frame_process(frame, "ws_stream", is_api=True)
                _, buffer = cv2.imencode('.jpg', frame)
                img_b64 = base64.b64encode(buffer).decode('utf-8')

                socketio.emit("stream_result", {
                    "detections": det_info,
                    "image": img_b64
                })

        threading.Thread(target=stream_loop).start()

    except Exception as e:
        emit("stream_error", {"error": str(e)})
        cap.release()
        print(f"⚠️ 处理流时发生错误: {str(e)}")
