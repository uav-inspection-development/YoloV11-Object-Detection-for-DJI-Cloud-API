import gradio as gr
import argparse
import torch
from train_det import train_det
from train_seg import train_seg


# Gradio 接口
def train_interface(task, workers, batch, device, data_name, epochs, img_size):
    if task == "Detection":
        return train_det(workers, batch, device, data_name, epochs, img_size)
    elif task == "Segmentation":
        return train_seg(workers, batch, device, data_name, epochs, img_size)
    else:
        return "无效的任务选择。请选择 'Detection' 或 'Segmentation'。"

# Gradio 接口
def launch_gradio():
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
    parser.add_argument("--gradio", action="store_true", help="启动 Gradio 界面。")

    args = parser.parse_args()

    if args.gradio:
        # 启动 Gradio 界面
        launch_gradio()
    else:
        # 根据命令行参数运行训练
        result = train_interface(args.task, args.workers, args.batch, args.device, args.data_name, args.epochs, args.img_size)
        print(result)