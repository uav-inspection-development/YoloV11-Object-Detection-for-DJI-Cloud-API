@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo 🚀 YOLO Detection System with MediaMTX 启动脚本
echo ==================================================

REM 检查 Docker 是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker 未安装，请先安装 Docker Desktop
    pause
    exit /b 1
)

REM 检查 Docker Compose 是否安装  
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose 未安装，请先安装 Docker Compose
    pause
    exit /b 1
)

REM 检查是否存在 .env 文件
if not exist .env (
    echo 📝 创建 .env 文件...
    copy .env.example .env >nul
    echo ✅ 已创建 .env 文件，请根据需要修改配置
)

REM 构建并启动服务
echo 🔨 构建并启动所有服务...
docker-compose up --build -d

REM 等待服务启动
echo ⏳ 等待服务启动...
timeout /t 10 /nobreak >nul

REM 检查服务状态
echo 📊 检查服务状态...
docker-compose ps

REM 显示访问信息
echo.
echo 🌐 服务访问信息：
echo ==================================================
echo YOLO 检测系统:     http://localhost:5000
echo MediaMTX Web 界面: http://localhost:8888
echo MediaMTX API:      http://localhost:9997
echo.
echo RTSP 服务器:       rtsp://localhost:8554
echo RTMP 服务器:       rtmp://localhost:1935
echo HLS 服务器:        http://localhost:8080
echo.

REM 显示示例 RTSP URL
echo 📡 示例 RTSP 地址：
echo ==================================================
echo 推流地址: rtsp://localhost:8554/your_stream_name
echo 拉流地址: rtsp://localhost:8554/your_stream_name
echo.

REM 显示常用命令
echo 🛠️ 常用命令：
echo ==================================================
echo 查看日志:     docker-compose logs -f
echo 停止服务:     docker-compose down
echo 重启服务:     docker-compose restart
echo.

echo ✅ 启动完成！请查看上述访问信息
echo.
echo 按任意键退出...
pause >nul
