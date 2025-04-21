import os
import torch
import yaml
from ultralytics import YOLO  # 导入YOLO模型
from QtFusion.path import abs_path
import matplotlib
matplotlib.use('TkAgg')


if __name__ == '__main__':  # 确保该模块被直接运行时才执行以下代码
    workers = 1
    batch = 2  # 适当等修改Batchsize，根据电脑等显存/内存设置，如果爆显存可以调低
    device = "0" if torch.cuda.is_available() else "cpu"

    data_path = abs_path(f'datasets/data/data.yaml', path_type='current')  # 数据集的yaml的绝对路径

    unix_style_path = data_path.replace(os.sep, '/')
    # 获取目录路径
    directory_path = os.path.dirname(unix_style_path)
    # 读取YAML文件，保持原有顺序
    with open(data_path, 'r') as file:
        data = yaml.load(file, Loader=yaml.FullLoader)
    # 修改path项
    if 'train' in data and 'val' in data and 'test' in data:
        data['train'] = directory_path + '/train'
        data['val'] = directory_path + '/val'
        data['test'] = directory_path + '/test'

        # 将修改后的数据写回YAML文件
        with open(data_path, 'w') as file:
            yaml.safe_dump(data, file, sort_keys=False)

    # 注意！不同模型大小不同，对设备等要求不同，如果要求较高的模型【报错】则换其他模型测试即可
    model = YOLO(model='./ultralytics/cfg/models/v11/yolo11s-seg.yaml', task='segment').load('./yolo11s-seg.pt')

    results = model.train(  # 开始训练模型
        data=data_path,  # 指定训练数据的配置文件路径
        device=device,  # 自动选择进行训练
        workers=workers,  # 指定使用2个工作进程加载数据
        imgsz=640,  # 指定输入图像的大小为640x640
        epochs=200,  # 指定训练100个epoch
        batch=batch,  # 指定每个批次的大小为8
    )
