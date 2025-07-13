#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RTSP 推流拉流测试脚本
用于测试 MediaMTX 服务器的 RTSP 功能
"""

import cv2
import time
import threading
import subprocess
import sys
import os

class RTSPTester:
    def __init__(self, mediamtx_host="localhost", rtsp_port=8554):
        self.mediamtx_host = mediamtx_host
        self.rtsp_port = rtsp_port
        self.base_url = f"rtsp://{mediamtx_host}:{rtsp_port}"
        
    def test_connection(self):
        """测试 MediaMTX 服务器连接"""
        try:
            import requests
            api_url = f"http://{self.mediamtx_host}:9997/v3/config/global/get"
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                print("✅ MediaMTX 服务器连接成功")
                return True
            else:
                print(f"❌ MediaMTX 服务器响应异常: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 无法连接到 MediaMTX 服务器: {e}")
            return False
    
    def create_test_video(self, output_path="test_video.mp4", duration=10):
        """创建测试视频文件"""
        print(f"📹 创建测试视频: {output_path}")
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, 30.0, (640, 480))
        
        for i in range(duration * 30):  # 30 FPS
            # 创建彩色测试图像
            frame = self.create_test_frame(i)
            out.write(frame)
            
        out.release()
        print(f"✅ 测试视频创建完成: {output_path}")
        return output_path
    
    def create_test_frame(self, frame_number):
        """创建测试帧"""
        import numpy as np
        
        # 创建 640x480 的彩色图像
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 添加彩色背景
        color = ((frame_number * 5) % 255, (frame_number * 3) % 255, (frame_number * 7) % 255)
        frame[:] = color
        
        # 添加移动的圆形
        center_x = int(320 + 200 * np.sin(frame_number * 0.1))
        center_y = int(240 + 100 * np.cos(frame_number * 0.1))
        cv2.circle(frame, (center_x, center_y), 50, (255, 255, 255), -1)
        
        # 添加帧号文本
        text = f"Frame: {frame_number}"
        cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        # 添加时间戳
        timestamp = f"Time: {time.strftime('%H:%M:%S')}"
        cv2.putText(frame, timestamp, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        
        return frame
    
    def push_test_stream(self, stream_name="test_stream", source_type="camera"):
        """推送测试流"""
        rtsp_url = f"{self.base_url}/{stream_name}"
        print(f"📡 开始推流到: {rtsp_url}")
        
        if source_type == "file":
            # 使用测试视频文件推流
            video_file = self.create_test_video()
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-re", "-stream_loop", "-1",
                "-i", video_file,
                "-c:v", "libx264", "-preset", "fast",
                "-c:a", "aac", "-strict", "experimental",
                "-f", "rtsp",
                rtsp_url
            ]
        else:
            # 使用虚拟摄像头推流
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", "testsrc2=size=640x480:rate=30",
                "-c:v", "libx264", "-preset", "fast",
                "-f", "rtsp",
                rtsp_url
            ]
        
        try:
            print(f"🔧 FFmpeg 命令: {' '.join(ffmpeg_cmd)}")
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # 等待几秒让推流稳定
            time.sleep(3)
            
            if process.poll() is None:
                print("✅ 推流进程启动成功")
                return process
            else:
                stdout, stderr = process.communicate()
                print(f"❌ 推流失败:")
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
                return None
                
        except FileNotFoundError:
            print("❌ 未找到 FFmpeg，请先安装 FFmpeg")
            return None
        except Exception as e:
            print(f"❌ 推流过程中出错: {e}")
            return None
    
    def pull_test_stream(self, stream_name="test_stream", duration=10):
        """拉取测试流"""
        rtsp_url = f"{self.base_url}/{stream_name}"
        print(f"📺 开始拉流: {rtsp_url}")
        
        cap = cv2.VideoCapture(rtsp_url)
        
        if not cap.isOpened():
            print(f"❌ 无法打开 RTSP 流: {rtsp_url}")
            return False
        
        print("✅ RTSP 流连接成功")
        
        frame_count = 0
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                ret, frame = cap.read()
                if not ret:
                    print("❌ 无法读取帧")
                    break
                
                frame_count += 1
                
                # 显示帧（可选）
                cv2.imshow(f'RTSP Stream - {stream_name}', frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
            print(f"✅ 成功接收 {frame_count} 帧")
            return True
            
        except Exception as e:
            print(f"❌ 拉流过程中出错: {e}")
            return False
        finally:
            cap.release()
            cv2.destroyAllWindows()
    
    def run_complete_test(self):
        """运行完整的 RTSP 测试"""
        print("🚀 开始 RTSP 完整测试")
        print("=" * 50)
        
        # 1. 测试连接
        if not self.test_connection():
            print("❌ 测试失败：无法连接到 MediaMTX 服务器")
            return False
        
        # 2. 启动推流
        push_process = self.push_test_stream("test_stream", "camera")
        if not push_process:
            print("❌ 测试失败：无法启动推流")
            return False
        
        # 3. 等待推流稳定
        print("⏳ 等待推流稳定...")
        time.sleep(5)
        
        # 4. 测试拉流
        print("📺 测试拉流...")
        pull_success = self.pull_test_stream("test_stream", duration=10)
        
        # 5. 停止推流
        print("🛑 停止推流...")
        push_process.terminate()
        push_process.wait()
        
        # 6. 清理
        if os.path.exists("test_video.mp4"):
            os.remove("test_video.mp4")
        
        if pull_success:
            print("✅ RTSP 测试完成：推流和拉流都正常工作")
            return True
        else:
            print("❌ RTSP 测试失败：拉流出现问题")
            return False

def main():
    """主函数"""
    print("🔍 RTSP 功能测试工具")
    print("=" * 50)
    
    # 检查是否在 Docker 环境中
    if os.path.exists("/.dockerenv"):
        mediamtx_host = "mediamtx"
        print("🐳 检测到 Docker 环境，使用服务名连接")
    else:
        mediamtx_host = "localhost"
        print("💻 本地环境，使用 localhost 连接")
    
    tester = RTSPTester(mediamtx_host=mediamtx_host)
    
    # 运行测试
    try:
        success = tester.run_complete_test()
        if success:
            print("\n🎉 所有测试通过！")
            sys.exit(0)
        else:
            print("\n💥 测试失败！")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 测试过程中出现未预期的错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
