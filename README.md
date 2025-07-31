# Automatic Solar Panel Detection of Photovoltaic Farms using Visible, EL, and Thermo Images

This project provides a comprehensive solution for detecting solar panel anomalies in photovoltaic farms using **Visible**, **EL (Electroluminescence)**, and **Thermo (Infrared)** images. It includes training a model, deploying it, and performing detection on images, videos, and real-time camera feeds.

---

## Steps to Run This Project

1. **Download the Dataset**:
    - [EL Crack Dataset](https://pan.baidu.com/s/11_Qj8LsRqgpXz4PLqeiE0w?pwd=d1dj)

2. **Prepare the Dataset**:
    - Copy the dataset into the project directory.
    - Follow the tutorial in the third step to train the model and generate the weight file `best.pt`. This file will be automatically saved in the `runs` folder after running `train.py`.

3. **Run the Detection Interface**:
    - Navigate to the `src` folder and execute `ui.py`.
    - Load the `best.pt` weight file in the interface.
    - Perform detection on images, videos, or real-time camera feeds for **Visible**, **EL**, or **Thermo** image types.

---

## Environment Deployment Steps

### 1. System Dependencies Installation

#### Automated Installation (Recommended)

For Ubuntu/Debian systems, use the provided script:

```bash
chmod +x install_system_deps.sh
./install_system_deps.sh
```

This script will:
- Detect your Ubuntu version
- Install appropriate OpenCV and OpenGL dependencies
- Handle package conflicts gracefully
- Provide fallbacks for older Ubuntu versions

#### Manual Installation

If you prefer to install manually or are using a different system:

**Ubuntu 22.04+ (Current LTS)**

```bash
sudo apt-get update
sudo apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgtk-3-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libatlas-base-dev \
    python3-dev \
    python3-numpy \
    libgl1-mesa-dev \
    libgles2-mesa-dev
```

**Ubuntu 20.04 (Older LTS)**

```bash
sudo apt-get update
sudo apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgtk-3-0 \
    python3-dev \
    python3-numpy
```

**Other Platforms**
- **CentOS/RHEL**: Use `yum` or `dnf` with equivalent package names
- **Arch Linux**: Use `pacman` with equivalent package names
- **Alpine**: Use `apk` with equivalent package names
- **Windows**: System dependencies are typically handled by Python packages themselves. You may need Visual C++ Redistributable and CUDA toolkit (if using GPU)
- **macOS**: `brew install opencv`

#### Docker Installation

If you're using Docker, add this to your Dockerfile:

```dockerfile
# Copy and run system dependencies installer
COPY install_system_deps.sh /tmp/
RUN chmod +x /tmp/install_system_deps.sh && /tmp/install_system_deps.sh
```

#### Verification

After installing system dependencies, verify the installation:

```bash
# Test Python imports
python -c "import cv2; print(f'OpenCV version: {cv2.__version__}')"

# Run the project validator (if available)
python tests/validate_config.py
```

### 2. Python Environment Setup

1. Create and activate a Python environment:

    ```shell
    conda create -n pytorch python=3.12
    conda activate pytorch
    ```

2. Install dependencies:

    ```shell
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    ```

3. Install torch and torchvision for CUDA:

    ```shell
    pip install torch==2.3.1+cu121 torchvision==0.18.0+cu121 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cu121
    ```

    - If you are using a CPU-only environment, use the following command instead:

    ```shell
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
    ```

4. Verify the environment:

    ```shell
    conda env list
    ```

5. If the following prompt appears:

    ```plaintext
    Downloading https://ultralytics.com/assets/Arial.ttf to 'C:\Users\ad\AppData\Roaming\Ultralytics\Arial.ttf'...
    ```

    - It means the configuration file is being downloaded automatically.
    - If a timeout occurs, copy the `Arial.ttf` file from the `fonts` folder to the specified path and rerun the code.

### 3. Docker Deployment with MediaMTX RTSP Support

This project includes Docker Compose configuration with integrated MediaMTX server for RTSP streaming capabilities.

#### Quick Start with Docker

1. **Start all services**:

    ```bash
    docker-compose up -d
    ```

2. **Check service status**:

    ```bash
    docker-compose ps
    ```

3. **View logs**:

    ```bash
    # All services
    docker-compose logs -f
    
    # Specific services
    docker-compose logs -f mediamtx
    docker-compose logs -f yolo-app
    ```

#### Service Ports

**MediaMTX Streaming Server**:

- **RTSP**: `8554` - Main RTSP push/pull streaming port
- **RTMP**: `1935` - RTMP streaming port  
- **HTTP/HLS**: `8080` - HLS streaming port
- **WebRTC**: `8889` - WebRTC port
- **Web Interface**: `8888` - MediaMTX web management interface
- **API**: `9997` - MediaMTX API endpoint

**YOLO Application**:

- **Streamlit**: `5000` - YOLO detection system web interface

#### RTSP Streaming Usage

**Push Stream (Send video to server)**:

```bash
# Push video file to server
ffmpeg -i input_video.mp4 -c copy -f rtsp rtsp://localhost:8554/mystream

# Push camera feed
ffmpeg -f dshow -i video="USB Camera" -c:v libx264 -preset fast -f rtsp rtsp://localhost:8554/camera_0

# Push file with loop
ffmpeg -re -stream_loop -1 -i input_video.mp4 -c copy -f rtsp rtsp://localhost:8554/test_stream
```

**Pull Stream (Receive video from server)**:

```bash
# Using VLC: Open Network Stream → rtsp://localhost:8554/mystream
# Using FFplay
ffplay rtsp://localhost:8554/mystream
```

**Python OpenCV Integration**:

```python
import cv2

# Connect to RTSP stream
cap = cv2.VideoCapture('rtsp://localhost:8554/mystream')

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    cv2.imshow('RTSP Stream', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

**Using RTSP in YOLO Detection**:

1. In the YOLO web interface, select "RTSP/RTMP Stream"
2. Enter RTSP URL: `rtsp://mediamtx:8554/camera_0`
3. Start detection

#### MediaMTX Web Management

Access the MediaMTX management interface at:

- URL: `http://localhost:8888`
- Features: View active streams, connection statistics, server status

#### Pre-configured Stream Paths

The system includes pre-configured stream paths:

- `yolo_input` - YOLO system input stream
- `yolo_output` - YOLO detection result output stream  
- `camera_0` - Camera 0
- `camera_1` - Camera 1

#### Troubleshooting

**Common issues**:

- **Cannot push stream**: Check firewall settings and ensure port 8554 is available
- **High latency**: Use FFmpeg parameters: `-preset ultrafast -tune zerolatency`
- **Connection refused**: Verify Docker services are running: `docker-compose ps`

**View detailed logs**:

```bash
# Set debug log level in mediamtx.yml: logLevel: debug
docker-compose restart mediamtx
docker-compose logs -f mediamtx
```

## Testing

Run the test suite with:

```bash
pytest
```

---

## Features

- **Multi-Image-Type Detection**:
  - Detect anomalies in solar panels using **Visible**, **EL**, and **Thermo** images.
  - Supports image, video, and real-time camera detection.

- **Custom Model Training**:
  - Train your own model using the provided dataset and `train.py`.

- **User-Friendly Interface**:
  - Load trained weights and perform detection through an interactive UI.

- **Customizable Detection Settings**:
  - Adjust confidence and IOU thresholds.
  - Select target classes for detection or segmentation.

---

## File Structure

```plaintext
demo_test/                    # Directory for demo test scripts
├── demo_test_camera.py       # Demo of testing camera
├── demo_test_contour.py      # Demo of testing contour
├── demo_test_image.py        # Demo of testing image
├── demo_test_video.py        # Demo of testing video
example/
├── EL/
│   ├── image/
│   ├── video/
├── Thermo/
│   ├── image/
│   ├── video/
├── Visible/
│   ├── image/
│   ├── video/
fonts/
├── Arial.ttf                 # Font file for visualization
icon/
├── ini.jpg                   # Icon for the application
output/
├── logs/
src/                          # Source code directory
├── _init_.py                 # Init
├── api_server.py             # Flask app for object detection
├── auth.py                   # Functions to verify OAuth2 tokens and get access tokens
├── check_license.py          # License verification and management
├── chinese_name.py           # Chinese name of labels
├── generate_license.py       # Script to generate license file
├── log.py                    # Tools for image/video processing and logging
├── model.py                  # YOLOv8 detector with model loading and processing
├── train_det.py              # Script of training detection model
├── train_interface.py        # Script of training entrance
├── train_seg.py              # Script of training segmentation model
├── ui.py                     # Main interface for detection
├── ui_style.py               # Custom CSS and HTML styles for Streamlit app
├── utils.py                  # Utility functions for preprocessing and postprocessing
├── web.py                    # Web interface for detection
ultralytics/                  # YOLOv8 source code
util_data/                    # Tools for processing non txt format datasets
├── util_dataset_augmentation.py     # Dataset augmentation tools
├── util_dataset_get_label_name.py   # Get label names from dataset
├── util_dataset_manipulation.py     # Dataset resizing tools
├── util_encryption.py               # Code encryption tools
├── util_image_visualization_detection.py      # Visualization tools
├── util_image_visualization_segmentation.py      # Visualization tools
├── util_via_to_yolo_conversion.py   # VIA to YOLO format conversion tools
├── util_voc_to_yolo_conversion.py   # VOC(XML) to YOLO(TXT) conversion tools
models/                       # Contains model definitions
runs/                         # Stores training results and weights
weights/                      # YOLO pre training weights for various versions
.gitignore                    # Git ignore file
AGENTS.md                     # Agent configuration for OpenAI Codex
CHANGELOG.md                  # Change log for project updates
CONTRIBUTING.md               # Contribution guidelines for the project
docker-compose.yml            # Docker Compose file for containerized deployment
Dockerfile                    # Dockerfile for building the application image
LICENSE                       # License file for the project
main.py                       # Main entry point for the application
README.md                     # Project overview and setup instructions
requirements.txt              # List of dependencies
User_Manual.md                # User manual for the application
```

---

## Example Usage

### Training the Model

1. **Place the dataset in the project `datasets` directory.**

2. **Run the Training Script Using Gradio Interface**:

    If you want to train the model using an interactive Gradio interface, run the following command:

    ```shell
    python src/train_interface.py --gradio
    ```

    **Explanation**:
    - This command launches a Gradio-based web interface in your browser.
    - You can select the task (`Detection` or `Segmentation`) and configure training parameters such as batch size, number of epochs, and image size.
    - Once configured, click the "Submit" button in the interface to start training.

3. **Run the Training Script Using Command Line**:

    If you prefer to train the model directly from the command line, use the following command:

    ```shell
    python src/train_interface.py --task Detection --workers 2 --batch 16 --device 0 --data_name data --epochs 50 --img_size 640
    ```

    **Parameter Explanation**:
    - `--task`: Specifies the training task. Use `Detection` for object detection or `Segmentation` for image segmentation.
    - `--workers`: Number of workers for data loading. Default is `1`.
    - `--batch`: Batch size for training. Default is `8`.
    - `--device`: Device to use for training. Use `0` for GPU or `cpu` for CPU.
    - `--data_name`: Name of the dataset. Default is `data`.
    - `--epochs`: Number of training epochs. Default is `200`.
    - `--img_size`: Input image size for training. Default is `640`.

    **Examples**:
    - To train a detection model:

      ```shell
      python src/train_interface.py --task Detection --workers 4 --batch 8 --device 0 --data_name my_dataset --epochs 100 --img_size 640
      ```

    - To train a segmentation model:

      ```shell
      python src/train_interface.py --task Segmentation --workers 2 --batch 16 --device cpu --data_name my_seg_dataset --epochs 50 --img_size 512
      ```

4. **Training Results**:

    - After training, the model weights (`best.pt` and `last.pt`) will be saved in the `runs/train/<task_name>` directory.
    - Training logs and metrics will also be stored in the same directory.

### Running the Detection Interface

1. **Generate a License File**:

    Before running the detection interface, you need to generate a license file. Use the following command:

    ```shell
    python src/generate_license.py --secret-key "0123456789abcdef0123456789abcdef" \
        --user-email "user@example.com" --license-id "LIC-000001" \
        --valid-until "2026-12-31" --output-path "license.dat" \
        --features 检测任务 分割任务 EL隐裂 红外 可见光
    ```

    **Explanation of Arguments**:
    - `--secret-key`: The secret key used for encrypting the license file.
    - `--user-email`: The email address of the user associated with the license.
    - `--license-id`: A unique identifier for the license.
    - `--valid-until`: The expiration date of the license in `YYYY-MM-DD` format. Use `"None"` for no expiration.
    - `--output-path`: The path where the generated license file will be saved (default: [license.dat](http://_vscodecontentref_/0)).
    - `--features`: Space-separated list of enabled features. Defaults to all features.

    **Example**:
    ```shell
    python src/generate_license.py --secret-key "0123456789abcdef0123456789abcdef" \
        --user-email "alice@example.com" --license-id "LIC-000002" \
        --valid-until "None" --output-path "license.dat" \
        --features 检测任务 红外
    ```

    After running this command, the encrypted license file will be saved to the specified path.

    The selected features determine which tasks and image types are available when running the detection interface.

2. **Run the Detection Interface with Login Interface**:

    ```shell
    python main.py
    ```

    After running this command, the streamlit login interface will be launched in your browser. Input the required parameters to log in.

3. **Run the Detection Interface with Command Line**:

    ```shell
    python main.py --run-mode=$RUN_MODE --oauth2-token-url=$OAUTH2_TOKEN_URL --client-id=$CLIENT_ID --client-secret=$CLIENT_SECRET --secret-key=$YOUR_SECRET_KEY --license-file=license.dat --bind-info-file=bind_info.json
    ```

    **Explanation of Arguments**:
    - `--run-mode`: Specifies the mode to run the application. Use option `streamlit` to launch the interactive Streamlit UI for detection.
    - `--oauth2-token-url`: The URL of the OAuth2 token endpoint used to retrieve access tokens (required if authentication is enabled).
    - `--client-id`: The client ID for the application, used to authenticate with the OAuth2 server.
    - `--client-secret`: The client secret for the application, used to authenticate with the OAuth2 server.
    - `--secret-key`: The secret key used for license encryption and decryption.
    - `--license-file`: Path to the license file (default: [license.dat](http://_vscodecontentref_/1)).
    - `--bind-info-file`: Path to the bind info file (default: [bind_info.json](http://_vscodecontentref_/2)).

4. **Run the Detection API Endpoints**:

    ```shell
    python main.py --run-mode=api --oauth2-introspect-url=$OAUTH2_INTROSPECT_URL --client-id=$CLIENT_ID --client-secret=$CLIENT_SECRET --secret-key=$YOUR_SECRET_KEY --license-file=license.dat --bind-info-file=bind_info.json
    ```

    **Explanation of Arguments**:
    - `--run-mode`: Specifies the mode to run the application. Use option `api` to launch the Flask API for programmatic access.
    - `--oauth2-introspect-url`: The URL of the OAuth2 introspection endpoint used to validate access tokens.
    - `--client-id`: The client ID for the application, used to authenticate with the OAuth2 server.
    - `--client-secret`: The client secret for the application, used to authenticate with the OAuth2 server.
    - `--secret-key`: The secret key used for license encryption and decryption.
    - `--license-file`: Path to the license file (default: [license.dat](http://_vscodecontentref_/3)).
    - `--bind-info-file`: Path to the bind info file (default: [bind_info.json](http://_vscodecontentref_/4)).

5. **Load the `best.pt` Weight File**:
    - Open the detection interface and load the trained weight file (`best.pt`).

6. **Select the Image Type**:
    - Choose the image type (**Visible**, **EL**, or **Thermo**) and start detection.

### Generate the executable File

#### Automated Build with Git Information (Recommended)

1. **Build with Git Information**:
    - Use the automated build script that includes Git commit information:
    ```shell
    python build_exe.py
    ```
    - This will automatically:
        - Collect Git repository information (commit hash, author, date, etc.)
        - Generate `src/git_info.py` with version details
        - Build `main.py` and other executables using PyInstaller
        - Clean up temporary files

2. **Build Specific Target**:
    - To build a specific file with Git information:
    ```shell
    # Build main.py with Git info
    python build_exe.py --target main.py --name "YoloV11-Main"
    
    # Build web interface with Git info
    python build_exe.py --target src/web.py --name "YoloV11-Web"
    ```

3. **Manual Git Information Collection**:
    - If you want to collect Git information separately:
    ```shell
    python collect_git_info.py --python src/git_info.py
    ```

#### Traditional Build Method

1. **Build the Executable**:
    - Use the following command to build the executable file for the application:
    ```shell
    pyinstaller main.py
    ```
    - This will create a standalone executable in the `dist` directory.

2. **Add the required files**:
    - Ensure that the following files are included in the `dist` directory:
        - The `fonts/` directory containing the `Arial.ttf` font file.
        - The `icon/` directory containing the application icon.
        - The `models/` directory containing the YOLOv8 model files.
    - Ensure that the following files are included in the `ui` directory:
        - The `license.dat` file generated earlier.

3. **Encrypt the `ui.py` File**:
    - Use the following command to encrypt the `ui.py` file:
    ```shell
    python utils_data/util_encryption.py --input-file src/ui.py --output-file src/ui_encrypted.py
    ```
    - This will create an encrypted version of the `ui.py` file named `ui_encrypted.py`.

4. **Move the Encrypted File**:
    - Move the `ui_encrypted.py` file to the `src/dist/main/_internal` directory, renaming it to `ui.py`:

5. **Run the Executable**:
    - After building the executable, navigate to the `dist/main` directory and run the application using the following command:
    ```shell
    ./main.exe --run-mode=streamlit --oauth2-token-url=$OAUTH2_TOKEN_URL --client-id=$CLIENT_ID --client-secret=$CLIENT_SECRET --secret-key=$YOUR_SECRET_KEY --license-file=license.dat --bind-info-file=bind_info.json
    ```

---

## Supported Detection Types

### Segmentation Tasks

- `component`: Solar panel component detection (单组件).
- `string`: Solar panel string detection (组串).

### Detection Tasks

#### Visible Light

- `yyzd`: Obstruction detection (遮挡).
- `ygfs`: Solar panel reflection detection (阳光反射).
- `zw`: Dirt/contamination detection (脏污).
- `yyzd_zw`: Obstruction and dirt detection (遮挡_脏污).
- `ns`: Bird excrement detection (鸟粪).
- `yyzd_ns`: Obstruction and bird excrement detection (遮挡_鸟粪).
- `zw_ns`: Dirt and bird excrement detection (脏污_鸟粪).
- `gfbzjbx`: Solar panel component deformation (光伏板组件变形).
- `gfbqs`: Solar panel missing detection (光伏板缺失).
- `mbsl`: Panel cracking detection (面板碎裂).
- `snow`: Snow accumulation detection (积雪).
- `crack`: Crack detection (隐裂).

#### Electroluminescence (EL)

- `crack`: Crack detection (隐裂).
- `missing_corner`: Missing corner detection (缺角).
- `fragment`: Fragment detection (碎片).
- `scratch`: Scratch detection (划伤).
- `black_cell`: Black cell detection (黑片).

#### Thermal (Infrared)

- `dyrb`: Single hot spot detection (单一热斑).
- `dmjrb`: Large area hot spot detection (大面积热斑).
- `dyrb_ycdw`: Single hot spot with abnormal low temperature (单一热斑_异常低温).
- `dmjrb_ycdw`: Large area hot spot with abnormal low temperature (大面积热斑_异常低温).
- `ycdw`: Abnormal low temperature detection (异常低温).
- `dyrb_ejgdl`: Single hot spot with diode short circuit (单一热斑_二极管短路).
- `ejgdl`: Diode short circuit detection (二极管短路).
- `ygfs`: Solar reflection detection (阳光反射).
- `gfb_zc_rcx`: Normal photovoltaic panel thermal imaging (光伏板正常热成像).
- `ejgdl_ycdw`: Diode short circuit with abnormal low temperature (二极管短路_异常低温).

## API Usage

The API server now supports Chinese and English internationalization, automatically switching languages based on requests or manual language configuration through API endpoints.

### Supported Languages

- `zh`: Chinese
- `en`: English

### Language Configuration

#### 1. Automatic Detection (Priority Order)

1. **Custom Header**: `X-Language: zh` or `X-Language: en`
2. **Query Parameter**: `?lang=zh` or `?lang=en`
3. **Accept-Language Header**: `Accept-Language: zh-CN,zh;q=0.9`

#### 2. Manual Configuration

```bash
# Set to English
curl -X POST http://localhost:5000/api/language \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{"language": "en"}'

# Set to Chinese  
curl -X POST http://localhost:5000/api/language \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{"language": "zh"}'
```

#### 3. Query Current Language

```bash
curl -X GET http://localhost:5000/api/language \
  -H "Authorization: Bearer your_token"
```

### Language-Specific API Responses

#### Chinese Mode `/api/types` Response

```json
{
  "检测任务": {
    "红外": [
      {"name": "Hot_Spot", "chinese_name": "热斑"},
      {"name": "Diode", "chinese_name": "二极管"}
    ],
    "可见光": [
      {"name": "Dust", "chinese_name": "灰尘"},
      {"name": "Crack", "chinese_name": "裂纹"}
    ],
    "EL隐裂": [
      {"name": "Break", "chinese_name": "断栅"}
    ],
    "其他": [
      {"name": "Bird", "chinese_name": "鸟类"}
    ]
  },
  "分割任务": {
    "红外": [...],
    "可见光": [...],
    "EL隐裂": [...]
  }
}
```

#### English Mode `/api/types` Response

```json
{
  "Detection Task": {
    "Thermal": [
      {"name": "Hot_Spot", "chinese_name": "热斑"},
      {"name": "Diode", "chinese_name": "二极管"}
    ],
    "Visible": [
      {"name": "Dust", "chinese_name": "灰尘"},
      {"name": "Crack", "chinese_name": "裂纹"}
    ],
    "EL": [
      {"name": "Break", "chinese_name": "断栅"}
    ],
    "Other": [
      {"name": "Bird", "chinese_name": "鸟类"}
    ]
  },
  "Segmentation Task": {
    "Thermal": [...],
    "Visible": [...],
    "EL": [...]
  }
}
```

### Internationalized Parameter Validation

Parameter validation error messages are returned in the current language setting:

#### Chinese Mode Error Example

```json
{
  "error": "Invalid parameters",
  "details": [
    "model_type must be '检测任务' or '分割任务'",
    "image_type must be one of ['可见光', '红外', 'EL隐裂', '其他']"
  ]
}
```

#### English Mode Error Example

```json
{
  "error": "Invalid parameters", 
  "details": [
    "model_type must be 'Detection Task' or 'Segmentation Task'",
    "image_type must be one of ['Visible', 'Thermal', 'EL', 'Other']"
  ]
}
```

### Best Practices

1. **Frontend Applications**: Use `X-Language` header to explicitly specify language
2. **Web Browsers**: Automatically use `Accept-Language` header
3. **Mobile Applications**: Use query parameters `?lang=zh` or `?lang=en`
4. **Persistent Settings**: Use `/api/language` API for long-term language configuration

### Important Notes

- Language settings affect all text content in API responses
- Type names (`name` field) remain in English for programmatic logic
- Chinese names (`chinese_name` field) are used for UI display
- Environment variable `API_LANGUAGE` can set the default language

### POST /api/detect/image

Detect objects in a single image.

#### Request

- **Method**: POST
- **URL**: `/api/detect/image`
- **Body**: JSON object containing the image file and config.

```json
{
    "image": "your image file",
    "conf_threshold": 0.5,
    "iou_threshold": 0.4,
    "model_type": "检测任务",
    "image_type": "红外",
    "selected_classes": [
        "dyrb",
        "dmjrb",
        "dyrb_ycdw",
        "dmjrb_ycdw",
        "ycdw",
        "dyrb_ejgdl",
        "ejgdl",
        "ygfs",
        "gfb_zc_rcx",
        "ejgdl_ycdw"
    ],
    "enable_pseudo_color": false,
    "undistortion_method": "不去除",
    "enable_rotate_correction": false,
    "enable_auto_keystone_correction": false,
    "enable_background_fill": false,
    "image_enhancement_method": "不处理",
}
```

#### Explanation of Parameters

- `image`: The image file to be processed.
- `conf_threshold`: Confidence threshold for detection (default: 0.5).
- `iou_threshold`: Intersection over Union threshold for non-max suppression (default: 0.4).
- `model_type`: Type of model to use for detection (e.g., "检测任务" for detection tasks, "分割任务" for segmentation tasks).
- `image_type`: Type of image (e.g., "红外" for infrared, "可见光" for visible light, "EL" for electroluminescence).
- `selected_classes`: List of classes to detect (e.g., ["dyrb", "dmjrb", "dyrb_ycdw", ...]).
- `enable_pseudo_color`: Whether to apply pseudo-coloring to the image (default: false).
- `undistortion_method`: Method for undistorting the image (default: "不去除" for no undistortion, "相机参数计算" for camera parameter calculation, "手动调整参数" for reading calibration files).
- `enable_rotate_correction`: Whether to enable rotation correction (default: false).
- `enable_auto_keystone_correction`: Whether to enable automatic keystone correction (default: false).
- `enable_background_fill`: Whether to enable background fill (default: false).
- `image_enhancement_method`: Method for enhancing the image (default: "不处理" for no enhancement, "CLAHE" for Contrast Limited Adaptive Histogram Equalization, "直方图均衡化" for histogram equalization).

#### Example

```bash
POST http://127.0.0.1:5000/api/detect/image
```

#### Response

```json
{
    "detections": [
        {
            "class_id": 0,
            "area": 3760,
            "name": "大面积热斑",
            "region": [
                11,
                202,
                58,
                282
            ],
            "time": "0.01",
            "type": "dmjrb"
        },
        {
            "class_id": 0,
            "area": 3680,
            "name": "大面积热斑",
            "region": [
                95,
                200,
                141,
                280
            ],
            "time": "0.01",
            "type": "dmjrb"
        },
        ...
    ]
}
```

#### Explanation of Response Parameters

- `detections`: List of detected objects in the image.
- `class_id`: ID of the detected class.
- `area`: Area of the detected object.
- `name`: Name of the detected class.
- `region`: Bounding box coordinates of the detected object in the format `[x1, y1, x2, y2]`, where `(x1, y1)` is the top-left corner and `(x2, y2)` is the bottom-right corner.
- `time`: Time taken for detection in seconds.
- `type`: Type of the detected object (e.g., "gfb_zc_rcx" for normal photovoltaic panel thermal imaging).

### POST /api/detect/video

Detect objects in a single video.

#### Request

- **Method**: POST
- **URL**: `/api/detect/video`
- **Body**: JSON object containing the video file and config.

```json
{
    "image": "your video file"
    "conf_threshold": 0.5,
    "iou_threshold": 0.4,
    "model_type": "检测任务",
    "image_type": "红外",
    "selected_classes": [
        "dyrb",
        "dmjrb",
        "dyrb_ycdw",
        "dmjrb_ycdw",
        "ycdw",
        "dyrb_ejgdl",
        "ejgdl",
        "ygfs",
        "gfb_zc_rcx",
        "ejgdl_ycdw"
    ],
    "enable_pseudo_color": false,
    "undistortion_method": "不去除",
    "enable_rotate_correction": false,
    "enable_auto_keystone_correction": false,
    "enable_background_fill": false,
    "image_enhancement_method": "不处理",
}
```

#### Explanation of Request Parameters

- `image`: The image file to be processed.
- `conf_threshold`: Confidence threshold for detection (default: 0.5).
- `iou_threshold`: Intersection over Union threshold for non-max suppression (default: 0.4).
- `model_type`: Type of model to use for detection (e.g., "检测任务" for detection tasks, "分割任务" for segmentation tasks).
- `image_type`: Type of image (e.g., "红外" for infrared, "可见光" for visible light, "EL" for electroluminescence).
- `selected_classes`: List of classes to detect (e.g., ["dyrb", "dmjrb", "dyrb_ycdw", ...]).
- `enable_pseudo_color`: Whether to apply pseudo-coloring to the image (default: false).
- `undistortion_method`: Method for undistorting the image (default: "不去除" for no undistortion, "相机参数计算" for camera parameter calculation, "手动调整参数" for reading calibration files).
- `enable_rotate_correction`: Whether to enable rotation correction (default: false).
- `enable_auto_keystone_correction`: Whether to enable automatic keystone correction (default: false).
- `enable_background_fill`: Whether to enable background fill (default: false).
- `image_enhancement_method`: Method for enhancing the image (default: "不处理" for no enhancement, "CLAHE" for Contrast Limited Adaptive Histogram Equalization, "直方图均衡化" for histogram equalization).

#### Example

```bash
POST http://127.0.0.1:5000/api/detect/video
```

#### Response

```json
{
    "results": [
        {
            "detections": [
                {
                    "class_id": 3,
                    "area": 10260,
                    "name": "光伏板正常热成像",
                    "region": [
                        501,
                        331,
                        577,
                        466
                    ],
                    "time": "0.02",
                    "type": "gfb_zc_rcx"
                },
                ...
            ],
            "frame": 0
        },
        ...
    ]
}
```

#### Explanation of Response Parameters

- `results`: List of detection results for each frame in the video.
- `detections`: List of detected objects in the frame.
- `class_id`: ID of the detected class.
- `area`: Area of the detected object.
- `name`: Name of the detected class.
- `region`: Bounding box coordinates of the detected object in the format `[x1, y1, x2, y2]`, where `(x1, y1)` is the top-left corner and `(x2, y2)` is the bottom-right corner.
- `time`: Time taken for detection in seconds.
- `type`: Type of the detected object (e.g., "gfb_zc_rcx" for normal photovoltaic panel thermal imaging).
- `frame`: Frame number in the video where the detections were made.

### GET /api/types

Retrieve the available detection types and their corresponding classes.

#### Request

- **Method**: GET
- **URL**: `/api/types`

#### Example

```bash
GET http://127.0.0.1:5000/api/types
```

#### Response

```json
{
    "分割任务": {
        "EL隐裂": [
            {
                "chinese_name": "太阳能板",
                "name": "solar_panel"
            }
        ],
        "可见光": [
            {
                "chinese_name": "太阳能板",
                "name": "solar_panel"
            }
        ],
        "红外": [
            {
                "chinese_name": "太阳能板",
                "name": "solar_panel"
            }
        ]
    },
    "检测任务": {
        "EL隐裂": [
            {
                "chinese_name": "隐裂",
                "name": "crack"
            },
            ...
        ],
        "其他": [
            {
                "chinese_name": "行人",
                "name": "people"
            },
            {
                "chinese_name": "车辆",
                "name": "vehicle"
            }
        ],
        "可见光": [
            {
                "chinese_name": "遮挡",
                "name": "yyzd"
            },
            ...
        ],
        "红外": [
            {
                "chinese_name": "单一热斑",
                "name": "dyrb"
            },
            ...
        ]
    }
}
```

#### Explanation of Response Parameters

- `分割任务`: List of segmentation tasks and their corresponding classes.
- `检测任务`: List of detection tasks and their corresponding classes.
- `chinese_name`: Chinese name of the class.
- `name`: English name of the class.

---

## Troubleshooting

- **Font Download Timeout**:
  - If the Arial font file fails to download, manually copy the `Arial.ttf` file from the `fonts` folder to the specified path.

- **Environment Issues**:
  - Ensure all dependencies are installed using the provided `requirements.txt`.

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---

## Acknowledgments

- Dataset provided by [EL Crack Dataset](https://pan.baidu.com/s/11_Qj8LsRqgpXz4PLqeiE0w?pwd=d1dj).
- Model training and detection powered by PyTorch and YOLO.

---

## 🔍 Git Version Information Integration

This project includes an advanced Git information integration system that automatically collects and displays version information in the application's "About" section when building with PyInstaller.

### 🚀 Features

- **Automatic Git Information Collection**: Collects commit hash, author, date, message, and repository details
- **Version Display**: Shows version information in the web application's "About" menu
- **Build Integration**: Seamlessly integrates with PyInstaller build process
- **Fallback Support**: Gracefully handles non-Git environments

### 📋 Displayed Information

The "About" menu will show:

- **Version Information**
  - Version tag (if available)
  - Commit hash (short form)
  - Branch name

- **Latest Commit**
  - Commit message
  - Author name and email
  - Commit date

- **Build Information**
  - Build timestamp
  - Total commit count
  - Repository URL

### 🛠 Usage

#### Quick Build (Recommended)
```shell
# Build all applications with Git information
python build_exe.py

# Build specific target
python build_exe.py --target main.py --name "YoloV11-Web"
```

#### Manual Process
```shell
# Step 1: Collect Git information
python collect_git_info.py --python src/git_info.py

# Step 2: Build with PyInstaller
pyinstaller --onefile main.py
```

#### Testing
```shell
# Test the Git integration system
python tests/test_git_integration.py
```

### 📁 Related Files

- `collect_git_info.py` - Git information collection script
- `build_exe.py` - Automated build script with Git integration
- `src/git_info.py` - Auto-generated Git information module
- `test_git_integration.py` - Integration test script
- `GIT_BUILD_GUIDE.md` - Detailed documentation

### 🔧 Benefits

1. **Version Tracking**: Easy identification of application version and source
2. **Issue Resolution**: Quick access to commit information for debugging
3. **Release Management**: Clear build information for distribution
4. **Automated Workflow**: No manual version management required

For detailed information, see [GIT_BUILD_GUIDE.md](GIT_BUILD_GUIDE.md).
