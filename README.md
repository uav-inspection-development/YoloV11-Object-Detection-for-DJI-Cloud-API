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
src/
├── train.py              # Script for training the model
├── ui.py                 # Main interface for detection
├── utils.py              # Utility functions for preprocessing and postprocessing
├── models/               # Contains model definitions
├── runs/                 # Stores training results and weights
fonts/
├── Arial.ttf             # Font file for visualization
requirements.txt          # List of dependencies
```

---

## Example Usage

### Training the Model

1. Place the dataset in the project `datasets` directory.

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

1. Run the detection interface:

    ```shell
    python src/ui.py --run-mode $RUN_MODE --oauth2-token-url $OAUTH2_TOKEN_URL --client-id $CLIENT_ID --client-secret $CLIENT_SECRET"
    ```

    **Explanation of Arguments**:
    - `--run-mode`: Specifies the mode to run the application. Use option `streamlit` to launch the interactive Streamlit UI for detection.
    - `--oauth2-token-url`: The URL of the OAuth2 token endpoint used to retrieve access tokens (required if authentication is enabled).
    - `--client-id`: The client ID for the application, used to authenticate with the OAuth2 server.
    - `--client-secret`: The client secret for the application, used to authenticate with the OAuth2 server.

2. Run the detection API endpoints:

    ```shell
    python src/ui.py --run-mode $RUN_MODE --oauth2-introspect-url $OAUTH2_INTROSPECT_URL --client-id $CLIENT_ID --client-secret $CLIENT_SECRET"
    ```

    **Explanation of Arguments**:
    - `--run-mode`: Specifies the mode to run the application. Use option `api` to launch the Flask API for programmatic access.
    - `--oauth2-introspect-url`: The URL of the OAuth2 introspection endpoint used to validate access tokens.
    - `--client-id`: The client ID for the application, used to authenticate with the OAuth2 server.
    - `--client-secret`: The client secret for the application, used to authenticate with the OAuth2 server.

3. Load the `best.pt` weight file in the interface.
4. Select the image type (**Visible**, **EL**, or **Thermo**) and start detection.

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
