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

1. Create and activate a Python environment:

    ```shell
    conda create -n pytorch python=3.10
    conda activate pytorch
    ```

2. Install dependencies:

    ```shell
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    ```

3. Verify the environment:

    ```shell
    conda env list
    ```

4. If the following prompt appears:

    ```plaintext
    Downloading https://ultralytics.com/assets/Arial.ttf to 'C:\Users\ad\AppData\Roaming\Ultralytics\Arial.ttf'...
    ```

    - It means the configuration file is being downloaded automatically.
    - If a timeout occurs, copy the `Arial.ttf` file from the `fonts` folder to the specified path and rerun the code.

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
tempDir/
ultralytics/                  # YOLOv8 source code
util_data/                    # Tools for processing non txt format datasets
├── encryption.py             # Code encryption tools
├── util_dataset_enhance.py   # Dataset enhancement tools
├── util_dataset_resize.py    # Dataset resizing tools
├── util_dataset_split.py     # Dataset splitting tools
├── util_visual.py            # Visualization tools
├── util_xml_to_txt_seg.py    # XML to TXT segmentation tools
├── util_xml_to_txt.py        # XML to TXT conversion tools
models/                       # Contains model definitions
runs/                         # Stores training results and weights
weights/                      # YOLO pre training weights for various versions
docker-compose.yml            # Docker Compose file for containerized deployment
Dockerfile                    # Dockerfile for building the application image
requirements.txt              # List of dependencies
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
    python src/generate_license.py --secret-key "0123456789abcdef0123456789abcdef" --user-email "user@example.com" --license-id "LIC-000001" --valid-until "2026-12-31" --output-path "license.dat"
    ```

    **Explanation of Arguments**:
    - `--secret-key`: The secret key used for encrypting the license file.
    - `--user-email`: The email address of the user associated with the license.
    - `--license-id`: A unique identifier for the license.
    - `--valid-until`: The expiration date of the license in `YYYY-MM-DD` format. Use `"None"` for no expiration.
    - `--output-path`: The path where the generated license file will be saved (default: [license.dat](http://_vscodecontentref_/0)).

    **Example**:
    ```shell
    python src/generate_license.py --secret-key "0123456789abcdef0123456789abcdef" --user-email "alice@example.com" --license-id "LIC-000002" --valid-until "None" --output-path "license.dat"
    ```

    After running this command, the encrypted license file will be saved to the specified path.

2. **Run the Detection Interface**:

    ```shell
    python src/ui.py --run-mode=$RUN_MODE --oauth2-token-url=$OAUTH2_TOKEN_URL --client-id=$CLIENT_ID --client-secret=$CLIENT_SECRET --secret-key=$YOUR_SECRET_KEY --license-file=license.dat --bind-info-file=bind_info.json
    ```

    **Explanation of Arguments**:
    - `--run-mode`: Specifies the mode to run the application. Use option `streamlit` to launch the interactive Streamlit UI for detection.
    - `--oauth2-token-url`: The URL of the OAuth2 token endpoint used to retrieve access tokens (required if authentication is enabled).
    - `--client-id`: The client ID for the application, used to authenticate with the OAuth2 server.
    - `--client-secret`: The client secret for the application, used to authenticate with the OAuth2 server.
    - `--secret-key`: The secret key used for license encryption and decryption.
    - `--license-file`: Path to the license file (default: [license.dat](http://_vscodecontentref_/1)).
    - `--bind-info-file`: Path to the bind info file (default: [bind_info.json](http://_vscodecontentref_/2)).

3. **Run the Detection API Endpoints**:

    ```shell
    python src/ui.py --run-mode=api --oauth2-introspect-url=$OAUTH2_INTROSPECT_URL --client-id=$CLIENT_ID --client-secret=$CLIENT_SECRET --secret-key=$YOUR_SECRET_KEY --license-file=license.dat --bind-info-file=bind_info.json
    ```

    **Explanation of Arguments**:
    - `--run-mode`: Specifies the mode to run the application. Use option `api` to launch the Flask API for programmatic access.
    - `--oauth2-introspect-url`: The URL of the OAuth2 introspection endpoint used to validate access tokens.
    - `--client-id`: The client ID for the application, used to authenticate with the OAuth2 server.
    - `--client-secret`: The client secret for the application, used to authenticate with the OAuth2 server.
    - `--secret-key`: The secret key used for license encryption and decryption.
    - `--license-file`: Path to the license file (default: [license.dat](http://_vscodecontentref_/3)).
    - `--bind-info-file`: Path to the bind info file (default: [bind_info.json](http://_vscodecontentref_/4)).

4. **Load the `best.pt` Weight File**:
    - Open the detection interface and load the trained weight file (`best.pt`).

5. **Select the Image Type**:
    - Choose the image type (**Visible**, **EL**, or **Thermo**) and start detection.

### Generate the executable File

1. **Build the Executable**:
    - Use the following command to build the executable file for the application:
    ```shell
    pyinstaller src/ui.py
    ```
    - This will create a standalone executable in the `dist` directory.

2. **Add the required files**:
    - Ensure that the following files are included in the `dist` directory:
        - The `fonts/` directory containing the `Arial.ttf` font file.
        - The `icon/` directory containing the application icon.
        - The `models/` directory containing the YOLOv8 model files.
    - Ensure that the following files are included in the `ui` directory:
        - The `license.dat` file generated earlier.

3. **Encrypt the `web.py` File**:
    - Use the following command to encrypt the `web.py` file:
    ```shell
    python src/encryption.py --input-file src/web.py --output-file src/web_encrypted.py
    ```
    - This will create an encrypted version of the `web.py` file named `web_encrypted.py`.

4. **Move the Encrypted File**:
    - Move the `web_encrypted.py` file to the `src/dist/ui/_internal` directory, renaming it to `web.py`:

5. **Run the Executable**:
    - After building the executable, navigate to the `dist/ui` directory and run the application using the following command:
    ```shell
    ./ui.exe --run-mode=streamlit --oauth2-token-url=$OAUTH2_TOKEN_URL --client-id=$CLIENT_ID --client-secret=$CLIENT_SECRET --secret-key=$YOUR_SECRET_KEY --license-file=license.dat --bind-info-file=bind_info.json
    ```

---

## API Usage

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
    "image_enhancement_method": "不处理",
}
```

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
            "extent": 3760,
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
            "extent": 3680,
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
    "image_enhancement_method": "不处理",
}
```

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
                    "extent": 10260,
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
