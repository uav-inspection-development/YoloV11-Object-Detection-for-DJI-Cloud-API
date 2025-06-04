
import socketio
import json

sio = socketio.Client()

# 配置参数（需与服务端要求一致）
REQUEST_PAYLOAD = {
    "params": {
        "conf_threshold": 0.5,
        "iou_threshold": 0.4,
        "model_type": "检测任务",
        "image_type": "红外",
        "selected_classes": ["dyrb","dmjrb","dyrb_ycdw","dmjrb_ycdw","ycdw","dyrb_ejgdl","ejgdl","ygfs","gfb_zc_rcx","ejgdl_ycdw"],
        "enable_pseudo_color": False,
        "undistortion_method": "不去除"
    },
    "stream_source": "0"  # 摄像头索引或视频流地址
}

# ---------- 事件监听 ----------
@sio.event
def connect():
    print("成功连接服务器，开始发送视频流请求...")
    # 发送视频流启动请求
    sio.emit('start_stream', REQUEST_PAYLOAD)  # 必须使用这个事件名称

@ sio.on('stream_result')  # 监听检测结果
def handle_stream_result(data):
    print("收到实时检测结果:")
    print(f"检测目标数量: {len(data['detections'])}")
    print(f"图像大小: {len(data['image'])} bytes")  # base64图像数据

    # 这里可以添加图像解码逻辑
    # import base64
    # img_data = base64.b64decode(data['image'])
    # ...

@ sio.on('stream_error')  # 监听错误信息
def handle_stream_error(err):
    print(f"视频流处理出错: {err['error']}")

# ---------- 启动连接 ----------
try:
    sio.connect('http://127.0.0.1:5000')
    sio.wait()  # 保持长连接
except Exception as e:
    print(f"连接异常: {str(e)}")