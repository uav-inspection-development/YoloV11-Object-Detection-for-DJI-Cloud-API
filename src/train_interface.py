import gradio as gr
import argparse
import torch
import os
from train_det import train_det
from train_seg import train_seg


def get_model_options(base_path="../ultralytics/cfg/models/"):
    """
    获取指定目录下的所有 YAML 文件路径，用于动态生成模型选择列表。

    Args:
        base_path (str): 模型配置文件的根目录。

    Returns:
        list: 包含所有可用 YAML 文件的相对路径。
    """
    model_options = []
    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith(".yaml"):
                relative_path = os.path.relpath(os.path.join(root, file), base_path)
                model_options.append(relative_path)
    return model_options

def get_pretrained_model_options(base_path="../weights/"):      # TODO: Change to abs path
    """
    获取指定目录下的所有 .pt 文件路径，用于动态生成预训练模型选择列表。

    Args:
        base_path (str): 预训练模型文件的根目录。

    Returns:
        list: 包含所有可用 .pt 文件的相对路径，首项为 None。
    """
    pretrained_model_options = ["None"]  # 将 None 作为第一个选项
    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith(".pt"):
                relative_path = os.path.relpath(os.path.join(root, file), base_path)
                pretrained_model_options.append(relative_path)
    return pretrained_model_options

def train_interface(task, workers, batch, device, data_name, epochs, img_size, pretrained_model=None, model_config=None, validate=False):
    """
    训练接口函数，根据任务类型选择相应的训练函数。
    """
    # 根据任务类型设置默认模型配置文件
    if model_config is None:
        if task == "Detection":
            print('###########################################')
            model_config = "../ultralytics/cfg/models/v11/yolo11.yaml"
        elif task == "Segmentation":
            model_config = "../ultralytics/cfg/models/v11/yolo11s-seg.yaml"

    # 如果选择了 "None"，将 pretrained_model 设置为 None
    if pretrained_model == "None":
        pretrained_model = None

    if task == "Detection":
        return train_det(workers, batch, device, data_name, epochs, img_size, pretrained_model, model_config, validate)
    elif task == "Segmentation":
        return train_seg(workers, batch, device, data_name, epochs, img_size, pretrained_model, model_config, validate)
    else:
        return "无效的任务选择。请选择 'Detection' 或 'Segmentation'。"

# Gradio 接口
def launch_gradio():
    """
    启动 Gradio 界面，提供用户友好的训练配置界面。
    """
    # 获取可用的模型配置文件选项
    model_options = get_model_options()
    # 获取可用的预训练模型选项
    pretrained_model_options = get_pretrained_model_options()

    interface = gr.Interface(
        fn=train_interface,
        inputs=[
            gr.Radio(["Detection", "Segmentation"], label="选择任务", info="选择要训练的任务。"),
            gr.Number(label="工作线程数", value=1, precision=0, info="用于数据加载的工作线程数，默认值为1。"),
            gr.Number(label="批次大小", value=8, precision=0, info="训练的批次大小，适当等修改Batchsize，根据电脑等显存/内存设置，如果爆显存可以调低，默认值为8。"),
            gr.Textbox(label="设备 (例如 '0' 表示 GPU 或 'cpu')", value="0" if torch.cuda.is_available() else "cpu", info="用于训练的设备，例如 '0' 表示 GPU 或 'cpu'。"),
            gr.Textbox(label="数据集名称", value="data", info="数据集的名称，例如 'data'。"),
            gr.Number(label="训练轮数", value=200, precision=0, info="训练的轮数，默认值为200。"),
            gr.Number(label="图像大小", value=640, precision=0, info="训练的图像大小，默认值为640。"),
            gr.Dropdown(choices=pretrained_model_options, label="预训练模型 (可选)", value="None", info="选择预训练模型的路径。如果选择 None，则不使用预训练模型。"),
            gr.Dropdown(choices=model_options, label="YOLO 模型配置文件", value="", info="选择 YOLO 模型配置文件。如果为空，将根据任务类型选择默认模型。"),
            gr.Checkbox(label="验证集评估", value=False, info="是否在每个 epoch 结束时对验证集进行评估。"),
        ],
        outputs="text",
        title="光伏云组件检测系统 YOLO 训练界面",
        description="选择任务 (Detection 或 Segmentation) 并配置训练参数以开始训练过程。"
    )
    interface.launch()

# 主函数，用于处理 argparse 和 Gradio
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="YOLO 训练界面")
    parser.add_argument("--task", type=str, choices=["Detection", "Segmentation"], help="选择要训练的任务 (Detection 或 Segmentation)。")
    parser.add_argument("--workers", type=int, default=1, help="用于数据加载的工作线程数，默认值为1。")
    parser.add_argument("--batch", type=int, default=8, help="训练的批次大小，适当等修改Batchsize，根据电脑等显存/内存设置，如果爆显存可以调低，默认值为8。")
    parser.add_argument("--device", type=str, default="0" if torch.cuda.is_available() else "cpu", help="用于训练的设备 (例如 '0' 表示 GPU 或 'cpu')，默认当前有GPU时为 '0'。")
    parser.add_argument("--data_name", type=str, default="data", help="数据集的名称，默认值为 'data'。")
    parser.add_argument("--epochs", type=int, default=200, help="训练的轮数，默认值为200。")
    parser.add_argument("--img_size", type=int, default=640, help="训练的图像大小，默认值为640。")
    parser.add_argument("--pretrained_model", type=str, default=None, help="预训练模型的路径。如果为空，则不使用预训练模型。")
    parser.add_argument("--model_config", type=str, default=None, help="YOLO 模型配置文件的路径。如果为空，将根据任务类型选择默认模型。")
    parser.add_argument("--validate", action="store_true", help="是否在每个 epoch 结束时对验证集进行评估。")
    parser.add_argument("--gradio", action="store_true", help="启动 Gradio 界面。")

    args = parser.parse_args()

    if args.gradio:
        # 启动 Gradio 界面
        launch_gradio()
    else:
        # 根据命令行参数运行训练
        result = train_interface(
            args.task,
            args.workers,
            args.batch,
            args.device,
            args.data_name,
            args.epochs,
            args.img_size,
            args.pretrained_model,
            args.model_config,
            args.validate
        )
        print(result)