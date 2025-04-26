from flask import Flask, request, jsonify, has_request_context
from flask_socketio import SocketIO, emit
import numpy as np
import cv2
import tempfile
import os
import sys
import base64
from web import Detection_UI
import threading
import json
from chinese_name_list import Visible_type, EL_type, Thermo_type, Segmentation_type, Other_type
from functools import wraps
import requests
from auth import verify_token, get_access_token


# 获取环境变量
OAUTH2_INTROSPECT_URL = os.getenv("OAUTH2_INTROSPECT_URL")
OAUTH2_TOKEN_URL = os.getenv("OAUTH2_TOKEN_URL")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# 验证环境变量是否存在
if not OAUTH2_INTROSPECT_URL or not CLIENT_ID or not CLIENT_SECRET:
    sys.stderr.write(
        "Error: Missing required environment variables.\n"
        "Please set the following variables:\n"
        "  - OAUTH2_INTROSPECT_URL\n"
        "  - CLIENT_ID\n"
        "  - CLIENT_SECRET\n"
    )
    sys.exit(1)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')


def require_oauth_token(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if has_request_context():
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                return jsonify({"error": "Missing or invalid Authorization header"}), 401
            token = auth.split(" ")[1]
            if not verify_token(token):
                return jsonify({"error": "Invalid or expired token"}), 403
        else:
            # WebSocket: 从 args[0] 中提取 token
            data = args[0] if args else {}
            token = data.get("access_token")
            if not token or not verify_token(token):
                emit("stream_error", {"error": "Missing or invalid token"})
                return
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
        if params["model_type"] not in ["检测任务", "分割任务"]:
            errors.append("model_type must be '检测任务' or '分割任务'")

    if "image_type" in params:
        if params["image_type"] not in ["可见光", "红外", "EL隐裂", "其他"]:
            errors.append("image_type must be one of ['可见光', '红外', 'EL隐裂', '其他']")

    if "selected_classes" in params and isinstance(params["selected_classes"], list):
        if not all(isinstance(cls, str) for cls in params["selected_classes"]):
            errors.append("All selected_classes must be strings")

        model_type = params.get("model_type", "检测任务")
        image_type = params.get("image_type", "可见光")
        if model_type == "分割任务":
            valid_classes = list(Segmentation_type.keys())
        elif image_type == "红外":
            valid_classes = list(Thermo_type.keys())
        elif image_type == "EL隐裂":
            valid_classes = list(EL_type.keys())
        elif image_type == "可见光":
            valid_classes = list(Visible_type.keys())
        else:
            valid_classes = list(Other_type.keys())

        for cls in params["selected_classes"]:
            if cls not in valid_classes:
                errors.append(f"Invalid selected_class '{cls}' for image_type '{image_type}'")

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
        "检测任务": {
            "红外": [
                {"name": "type1", "chinese_name": "类型1"},
                {"name": "type2", "chinese_name": "类型2"}
            ],
            "EL隐裂": [
                {"name": "type3", "chinese_name": "类型3"}
            ],
            "可见光": [
                {"name": "type4", "chinese_name": "类型4"}
            ],
            "其他": [
                {"name": "type8", "chinese_name": "类型5"}
            ]
        },
        "分割任务": {
            "红外": [
                {"name": "type5", "chinese_name": "类型6"}
            ],
            "EL隐裂": [
                {"name": "type6", "chinese_name": "类型7"}
            ],
            "可见光": [
                {"name": "type7", "chinese_name": "类型8"}
            ]
        }
    }
    """
    try:
        tasks = {
            "检测任务": {
                "红外": Thermo_type,
                "EL隐裂": EL_type,
                "可见光": Visible_type,
                "其他": Other_type
            },
            "分割任务": {
                "红外": Segmentation_type,
                "EL隐裂": Segmentation_type,
                "可见光": Segmentation_type
            }
        }

        # Format the response
        response = {
            "检测任务": {
                panel_type: [
                    {"name": name, "chinese_name": chinese_name}
                    for name, chinese_name in task.items()
                ]
                for panel_type, task in tasks["检测任务"].items()
            },
            "分割任务": {
                panel_type: [
                    {"name": name, "chinese_name": chinese_name}
                    for name, chinese_name in task.items()
                ]
                for panel_type, task in tasks["分割任务"].items()
            }
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route("/api/detect/image", methods=["POST"])
@require_oauth_token
@validate_params(["conf_threshold", "iou_threshold", "model_type", "image_type", "selected_classes"])
def detect_image(validated_params, files):
    """
    Detect objects in an uploaded image.

    Example Input:
    Form-data:
    - image: (binary file) The image file to be processed.
    - conf_threshold: 0.5
    - iou_threshold: 0.4
    - model_type: "检测任务"
    - image_type: "可见光"
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
        img_file = files.get("image")
        if not img_file:
            return jsonify({"error": "No image uploaded"}), 400

        img_data = np.frombuffer(img_file.read(), np.uint8)
        image = cv2.imdecode(img_data, cv2.IMREAD_COLOR)

        detector = Detection_UI(from_streamlit=False, api_params=validated_params)
        _, det_info, _ = detector.frame_process(image, "api_image.jpg")
        return jsonify({"detections": det_info})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/detect/video", methods=["POST"])
@require_oauth_token
@validate_params(["conf_threshold", "iou_threshold", "model_type", "image_type", "selected_classes"])
def detect_video(validated_params, files):
    """
    Detect objects in an uploaded video.

    Example Input:
    Form-data:
    - video: (binary file) The video file to be processed.
    - conf_threshold: 0.5
    - iou_threshold: 0.4
    - model_type: "检测任务"
    - image_type: "可见光"
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
        detector = Detection_UI(from_streamlit=False, api_params=validated_params)
        frame_results = []
        frame_id = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            _, det_info, _ = detector.frame_process(frame, f"frame_{frame_id}.jpg")
            if det_info:
                frame_results.append({
                    "frame": frame_id,
                    "detections": det_info
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
@validate_params(["conf_threshold", "iou_threshold", "model_type", "image_type", "selected_classes"])
def handle_stream(params, stream_source):
    """
    Handle real-time video stream detection.

    Example Input:
    WebSocket message:
    {
        "params": {
            "conf_threshold": 0.5,
            "iou_threshold": 0.4,
            "model_type": "检测任务",
            "image_type": "可见光",
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
        if isinstance(stream_source, str) and stream_source.isdigit():
            stream_source = int(stream_source)

        cap = cv2.VideoCapture(stream_source)
        if not cap.isOpened():
            emit("stream_error", {"error": f"Unable to open stream: {stream_source}"})
            return

        detector = Detection_UI(from_streamlit=False, api_params=params)

        def stream_loop():
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                _, det_info, _ = detector.frame_process(frame, "ws_stream")
                _, buffer = cv2.imencode('.jpg', frame)
                img_b64 = base64.b64encode(buffer).decode('utf-8')

                emit("stream_result", {
                    "detections": det_info,
                    "image": img_b64
                }, broadcast=False)

        threading.Thread(target=stream_loop).start()

    except Exception as e:
        emit("stream_error", {"error": str(e)})

