import gradio as gr
import argparse
import torch
import os
import sys
import threading
import queue
import time
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
from train_det import train_det
from train_seg import train_seg


class ProgressCapture:
    """捕获训练进度的类"""
    def __init__(self):
        self.output_queue = queue.Queue()
        self.captured_output = StringIO()
        
    def write(self, text):
        """重定向输出到队列"""
        if text.strip():  # 只添加非空内容
            self.output_queue.put(text)
            self.captured_output.write(text)
        return len(text)
    
    def flush(self):
        """刷新缓冲区"""
        pass
    
    def get_latest_output(self):
        """获取最新的输出内容"""
        output_lines = []
        try:
            while True:
                line = self.output_queue.get_nowait()
                output_lines.append(line)
        except queue.Empty:
            pass
        return ''.join(output_lines)
    
    def get_all_output(self):
        """获取所有输出内容"""
        return self.captured_output.getvalue()


def train_interface_with_progress(task, workers, batch, device, dataset_dir, epochs, img_size, pretrained_model=None, model_config=None, validate=False, progress=gr.Progress()):
    """
    带进度显示的训练接口函数
    """
    # 获取实际的文件路径
    model_options = get_model_options()
    model_choices = {os.path.basename(option): option for option in model_options}
    pretrained_model_options = get_pretrained_model_options()
    pretrained_model_choices = {os.path.basename(option): option for option in pretrained_model_options}
    
    # 将选择的文件名转换为实际路径
    if model_config and model_config in model_choices:
        model_config = model_choices[model_config]
    if pretrained_model and pretrained_model in pretrained_model_choices:
        pretrained_model = pretrained_model_choices[pretrained_model]
    
    # 创建进度捕获器
    progress_capture = ProgressCapture()
    result_container = {"result": None}
    
    def run_training():
        """在单独线程中运行训练"""
        try:
            # 重定向标准输出和错误输出
            original_stdout = sys.stdout
            original_stderr = sys.stderr
            sys.stdout = progress_capture
            sys.stderr = progress_capture
            
            # 调用原始训练函数
            result = train_interface(task, workers, batch, device, dataset_dir, epochs, img_size, pretrained_model, model_config, validate)
            result_container["result"] = result
            
            # 恢复原始输出
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            
        except Exception as e:
            # 恢复原始输出
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            result_container["result"] = f"训练过程中发生错误: {str(e)}"
    
    # 在单独线程中启动训练
    training_thread = threading.Thread(target=run_training)
    training_thread.daemon = True
    training_thread.start()
    
    # 实时更新进度
    accumulated_output = ""
    last_metrics = {}
    
    while training_thread.is_alive():
        latest_output = progress_capture.get_latest_output()
        if latest_output:
            accumulated_output += latest_output
            
            # 解析训练指标
            metrics = parse_training_metrics(accumulated_output)
            
            if metrics.get('epoch_progress'):
                progress_value = metrics['epoch_progress']
                current_epoch = metrics.get('current_epoch', 0)
                total_epochs = metrics.get('total_epochs', epochs)
                
                # 构建进度描述
                desc_parts = [f"Epoch {current_epoch}/{total_epochs}"]
                if metrics.get('loss'):
                    desc_parts.append(f"Loss: {metrics['loss']:.4f}")
                if metrics.get('map'):
                    desc_parts.append(f"mAP: {metrics['map']:.4f}")
                
                desc = "训练中... " + " | ".join(desc_parts)
                progress(progress_value, desc=desc)
            
            # 格式化输出
            formatted_output = format_training_output(accumulated_output)
            yield formatted_output
        
        time.sleep(0.5)  # 每0.5秒更新一次
    
    # 训练完成后获取最终输出
    final_output = progress_capture.get_all_output()
    if result_container["result"]:
        final_output += f"\n\n🎉 训练结果: {result_container['result']}"
    
    if not final_output.strip():
        final_output = "✅ 训练完成！"
    
    # 格式化最终输出
    formatted_final_output = format_training_output(final_output)
    
    progress(1.0, desc="🎉 训练完成!")
    yield formatted_final_output


def get_model_options(base_path="../ultralytics/cfg/models/"):
    """
    获取指定目录下的所有 YAML 文件路径，用于动态生成模型选择列表。

    Args:
        base_path (str): 模型配置文件的根目录。

    Returns:
        list: 包含所有可用 YAML 文件的相对路径。
    """
    root_folder = os.path.dirname(os.path.abspath(__file__))  # Get the current script's directory
    absolute_base_path = os.path.join(root_folder, base_path)

    model_options = []
    for root, _, files in os.walk(absolute_base_path):
        for file in files:
            if file.endswith(".yaml"):
                absolute_path = os.path.join(root, file)
                model_options.append(absolute_path)
    return model_options

def get_pretrained_model_options(base_path="../weights/"):
    """
    获取指定目录下的所有 .pt 文件路径，用于动态生成预训练模型选择列表。

    Args:
        base_path (str): 预训练模型文件的根目录。

    Returns:
        list: 包含所有可用 .pt 文件的相对路径，首项为 None。
    """
    root_folder = os.path.dirname(os.path.abspath(__file__))
    absolute_base_path = os.path.join(root_folder, base_path)

    pretrained_model_options = ["None"]  # 将 None 作为第一个选项
    for root, _, files in os.walk(absolute_base_path):
        for file in files:
            if file.endswith(".pt"):
                absolute_path = os.path.join(root, file)
                pretrained_model_options.append(absolute_path)
    return pretrained_model_options

def train_interface(task, workers, batch, device, dataset_dir, epochs, img_size, pretrained_model=None, model_config=None, validate=False):
    """
    训练接口函数，根据任务类型选择相应的训练函数。
    """
    # 获取当前脚本所在的根目录
    root_folder = os.path.dirname(os.path.abspath(__file__))

    # 根据任务类型设置默认模型配置文件
    if model_config is None or model_config == "":
        if task == "Detection":
            model_config = os.path.join(root_folder, "../ultralytics/cfg/models/v11/yolo11.yaml")
        elif task == "Segmentation":
            model_config = os.path.join(root_folder, "../ultralytics/cfg/models/v11/yolo11s-seg.yaml")

    # 如果选择了 "None"，将 pretrained_model 设置为 None
    if pretrained_model == "None":
        pretrained_model = None

    if task == "Detection":
        return train_det(workers, batch, device, dataset_dir, epochs, img_size, pretrained_model, model_config, validate)
    elif task == "Segmentation":
        return train_seg(workers, batch, device, dataset_dir, epochs, img_size, pretrained_model, model_config, validate)
    else:
        return "无效的任务选择。请选择 'Detection' 或 'Segmentation'。"

def parse_training_metrics(output_text):
    """
    从训练输出中解析指标信息
    """
    metrics = {}
    lines = output_text.split('\n')
    
    for line in lines:
        # 解析epoch信息
        if 'Epoch' in line and '/' in line:
            try:
                # 查找类似 "Epoch 1/100" 的模式
                import re
                epoch_match = re.search(r'Epoch\s+(\d+)/(\d+)', line)
                if epoch_match:
                    current_epoch = int(epoch_match.group(1))
                    total_epochs = int(epoch_match.group(2))
                    metrics['current_epoch'] = current_epoch
                    metrics['total_epochs'] = total_epochs
                    metrics['epoch_progress'] = current_epoch / total_epochs
            except:
                pass
        
        # 解析损失值
        if 'loss' in line.lower():
            try:
                # 查找损失值
                import re
                loss_matches = re.findall(r'loss[:\s]*([0-9.]+)', line.lower())
                if loss_matches:
                    metrics['loss'] = float(loss_matches[0])
            except:
                pass
        
        # 解析mAP值
        if 'map' in line.lower() or 'map50' in line.lower():
            try:
                import re
                map_matches = re.findall(r'map[0-9]*[:\s]*([0-9.]+)', line.lower())
                if map_matches:
                    metrics['map'] = float(map_matches[0])
            except:
                pass
    
    return metrics

def format_training_output(output_text):
    """
    格式化训练输出，使其更易读
    """
    lines = output_text.split('\n')
    formatted_lines = []
    
    for line in lines:
        # 高亮重要信息
        if 'Epoch' in line:
            formatted_lines.append(f"🔄 {line}")
        elif 'loss' in line.lower():
            formatted_lines.append(f"📉 {line}")
        elif 'map' in line.lower():
            formatted_lines.append(f"📊 {line}")
        elif 'best' in line.lower():
            formatted_lines.append(f"🏆 {line}")
        elif 'saved' in line.lower():
            formatted_lines.append(f"💾 {line}")
        elif any(keyword in line.lower() for keyword in ['error', 'failed', 'exception']):
            formatted_lines.append(f"❌ {line}")
        elif any(keyword in line.lower() for keyword in ['complete', 'finished', 'done']):
            formatted_lines.append(f"✅ {line}")
        else:
            formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)

# Gradio 接口
def launch_gradio():
    """
    启动 Gradio 界面，提供用户友好的训练配置界面。
    """
    # 获取可用的模型配置文件选项
    model_options = get_model_options()
    model_choices = {os.path.basename(option): option for option in model_options}
    # 获取可用的预训练模型选项
    pretrained_model_options = get_pretrained_model_options()
    pretrained_model_choices = {os.path.basename(option): option for option in pretrained_model_options}

    with gr.Blocks(title="光伏云组件检测系统 YOLO 训练界面") as interface:
        gr.Markdown("# 光伏云组件检测系统 YOLO 训练界面")
        gr.Markdown("选择任务 (Detection 或 Segmentation) 并配置训练参数以开始训练过程。")
        
        with gr.Row():
            with gr.Column(scale=1):
                task = gr.Radio(["Detection", "Segmentation"], value="Detection", label="选择任务", info="选择要训练的任务。")
                workers = gr.Number(label="工作线程数", value=8, precision=0, info="用于数据加载的工作线程数，默认值为8。")
                batch = gr.Number(label="批次大小", value=32, precision=0, info="训练的批次大小，适当等修改Batchsize，根据电脑等显存/内存设置，如果爆显存可以调低，默认值为32。")
                device = gr.Textbox(label="设备 (例如 '0' 表示 GPU 或 'cpu')", value="0" if torch.cuda.is_available() else "cpu", info="用于训练的设备，例如 '0' 表示 GPU 或 'cpu'。")
                dataset_dir = gr.Textbox(label="数据集文件夹路径", value="../datasets/data", info="数据集文件夹的绝对路径，需包含data.yaml、images、labels等。")
                epochs = gr.Number(label="训练轮数", value=200, precision=0, info="训练的轮数，默认值为200。")
                img_size = gr.Number(label="图像大小", value=640, precision=0, info="训练的图像大小，默认值为640。")
                pretrained_model = gr.Dropdown(choices=list(pretrained_model_choices.keys()), label="预训练模型 (可选)", value="None", info="选择预训练模型的路径。如果选择 None，则不使用预训练模型。")
                model_config = gr.Dropdown(choices=list(model_choices.keys()), label="YOLO 模型配置文件", value="yolo11.yaml", info="选择 YOLO 模型配置文件。如果为空，将根据任务类型选择默认模型。")
                validate = gr.Checkbox(label="验证集评估", value=False, info="是否在每个 epoch 结束时对验证集进行评估。")
                
                train_btn = gr.Button("开始训练", variant="primary", size="lg")
                stop_btn = gr.Button("停止训练", variant="stop", size="lg")
            
            with gr.Column(scale=2):
                output_text = gr.Textbox(
                    label="训练输出", 
                    lines=30, 
                    max_lines=50,
                    autoscroll=True,
                    interactive=False,
                    show_copy_button=True
                )
        
        # 训练事件处理
        train_event = train_btn.click(
            fn=train_interface_with_progress,
            inputs=[task, workers, batch, device, dataset_dir, epochs, img_size, pretrained_model, model_config, validate],
            outputs=[output_text],
            show_progress=True
        )
        
        # 停止训练事件
        stop_btn.click(fn=None, cancels=[train_event])

    interface.launch()

# 主函数，用于处理 argparse 和 Gradio
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="YOLO 训练界面")
    parser.add_argument("--task", type=str, choices=["Detection", "Segmentation"], default="Detection", help="选择要训练的任务 (Detection 或 Segmentation)。")
    parser.add_argument("--workers", type=int, default=8, help="用于数据加载的工作线程数，默认值为8。")
    parser.add_argument("--batch", type=int, default=32, help="训练的批次大小，适当等修改Batchsize，根据电脑等显存/内存设置，如果爆显存可以调低，默认值为32。")
    parser.add_argument("--device", type=str, default="0" if torch.cuda.is_available() else "cpu", help="用于训练的设备 (例如 '0' 表示 GPU 或 'cpu')，默认当前有GPU时为 '0'。")
    parser.add_argument("--dataset_dir", type=str, default="../datasets/data", help="数据集文件夹的绝对路径，需包含data.yaml、images、labels等。")
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
            args.dataset_dir,
            args.epochs,
            args.img_size,
            args.pretrained_model,
            args.model_config,
            args.validate
        )
        print(result)