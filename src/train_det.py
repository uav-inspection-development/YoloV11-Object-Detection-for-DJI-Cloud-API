import os
import sys
import datetime
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# 添加上级目录到系统路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import yaml
from ultralytics import YOLO  # 导入YOLO模型
from QtFusion.path import abs_path


def train_det(workers, batch, device, dataset_dir, epochs, img_size, pretrained_model=None, model_config='../ultralytics/cfg/models/v11/yolo11.yaml', validate=False):
    """
    训练检测模型的函数。

    Args:
        workers (int): 用于数据加载的工作线程数。
        batch (int): 训练的批次大小。
        device (str): 用于训练的设备 (例如 '0' 表示 GPU 或 'cpu')。
        dataset_dir (str): 数据集文件夹路径，需包含data.yaml、images、labels等。
        epochs (int): 训练的轮数。
        img_size (int): 训练的图像大小。
        pretrained_model (str, optional): 预训练模型的路径。如果提供，将加载该模型进行训练。默认为 None。
        model_config (str, optional): YOLO 模型配置文件的路径。默认为 '../ultralytics/cfg/models/v11/yolo11.yaml'。
        validate (bool, optional): 是否在每个 epoch 结束时对验证集进行评估。默认为 False。
    """
    try:
        # 获取data.yaml的绝对路径
        data_path = abs_path(os.path.join(dataset_dir, "data.yaml"), path_type='current')
        unix_style_path = data_path.replace(os.sep, '/')

        # 检查数据集配置文件是否存在
        if not os.path.exists(data_path):
            return f"数据集配置文件未找到: {data_path}. 请确保数据集存在。"

        # 检查数据集配置文件是否存在
        if not os.path.exists(data_path):
            return f"数据集配置文件未找到: {data_path}. 请确保数据集存在。"

        # 读取YAML文件，保持原有顺序
        with open(data_path, 'r') as file:
            data = yaml.load(file, Loader=yaml.FullLoader)
        # 自动修正路径
        directory_path = os.path.dirname(unix_style_path)
        if 'path' in data:
            data['path'] = directory_path
            with open(data_path, 'w') as file:
                yaml.safe_dump(data, file, sort_keys=False)
        if 'train' in data and 'val' in data and 'test' in data:
            data['train'] = directory_path + '/images/train'
            data['val'] = directory_path + '/images/val'
            data['test'] = directory_path + '/images/test'
            with open(data_path, 'w') as file:
                yaml.safe_dump(data, file, sort_keys=False)

        try:
            # 初始化 YOLO 模型，注意！不同模型大小不同，对设备等要求不同，如果要求较高的模型【报错】则换其他模型测试即可
            if pretrained_model:
                # 如果提供了预训练模型路径，则加载该模型
                model = YOLO(model=model_config, task='detect').load(pretrained_model)
            else:
                # 否则初始化一个新的模型
                model = YOLO(model=model_config, task='detect')
        except Exception as e:
            return f"模型加载失败: {str(e)}. 请检查预训练模型或配置文件是否正确。"

        # 生成当前时间字符串
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        task_name = f'detection_task_{os.path.basename(os.path.normpath(dataset_dir))}_{current_time}'

        results = model.train(  # 开始训练模型
            data=data_path,  # 指定训练数据的配置文件路径
            device=device,  # 自动选择进行训练
            workers=workers,  # 指定使用2个工作进程加载数据
            imgsz=img_size,  # 指定输入图像的大小
            epochs=epochs,  # 指定训练的epoch轮数
            batch=batch,  # 指定每个批次的大小
            name=task_name,  # 指定训练任务的名称
            val=validate  # 在每个 epoch 结束时对验证集进行评估
        )

        # 获取保存目录路径
        save_dir = results.save_dir

        # 自定义保存的模型文件名
        best_model_path = save_dir / f"{task_name}_best.pt"
        last_model_path = save_dir / f"{task_name}_last.pt"

        # 重命名默认的模型文件
        os.rename(save_dir / 'weights' / 'best.pt', best_model_path)
        os.rename(save_dir / 'weights' / 'last.pt', last_model_path)

        # 格式化结果以供 Gradio 输出
        return (
            f"检测任务训练成功完成！\n"
            f"任务名称: {task_name}\n"
            f"最佳模型路径: {best_model_path}\n"
            f"最后模型路径: {last_model_path}\n"
            # f"训练指标:\n"
            # f"  - 最终训练损失: {results.metrics['train_loss']:.4f}\n"
            # f"  - 最终验证损失: {results.metrics['val_loss']:.4f}\n"
            # f"  - mAP@50: {results.metrics['mAP_50']:.4f}\n"
            # f"  - mAP@50-95: {results.metrics['mAP_50_95']:.4f}\n"
        )
    except Exception as e:
        return f"检测任务训练失败: {str(e)}"  # 返回错误信息
