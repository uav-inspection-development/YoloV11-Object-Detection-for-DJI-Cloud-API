# -*- coding: utf-8 -*-
import cv2  # 导入OpenCV库，用于处理图像和视频
import torch
import numpy as np  # 导入numpy库
from QtFusion.models import Detector, HeatmapGenerator  # 从QtFusion库中导入Detector抽象基类
# from chinese_name_list import Chinese_name  # 从datasets库中导入Chinese_name字典，用于获取类别的中文名称
from ultralytics import YOLO  # 从ultralytics库中导入YOLO类，用于加载YOLO模型
from ultralytics.utils.torch_utils import select_device  # 从ultralytics库中导入select_device函数，用于选择设备
import os
device = "cuda:0" if torch.cuda.is_available() else "cpu"

ini_params = {
    'device': device,  # 设备类型，这里设置为CPU
    'conf': 0.05,  # 物体置信度阈值
    'iou': 0.2,  # 用于非极大值抑制的IOU阈值
    'classes': None,  # 类别过滤器，这里设置为None表示不过滤任何类别
    'verbose': False
}


def count_classes(det_info, class_names):
    """
    Count the number of each class in the detection info.

    :param det_info: List of detection info, each item is a list like [class_name, bbox, conf, class_id]
    :param class_names: List of all possible class names
    :return: A list with counts of each class
    """
    count_dict = {name: 0 for name in class_names}  # 创建一个字典，用于存储每个类别的数量
    for info in det_info:  # 遍历检测信息
        class_name = info['class_name']  # 获取类别名称
        if class_name in count_dict:  # 如果类别名称在字典中
            count_dict[class_name] += 1  # 将该类别的数量加1

    # Convert the dictionary to a list in the same order as class_names
    count_list = [count_dict[name] for name in class_names]  # 将字典转换为列表，列表的顺序与class_names相同
    return count_list  # 返回列表


class Web_Detector(Detector):  # 定义YOLOv8Detector类，继承自Detector类
    def __init__(self, params=None):  # 定义构造函数
        super().__init__(params)  # 调用父类的构造函数
        self.model = None
        self.img = None  # 初始化图像为None
        self.names = []  # 初始化类别的中文名称为空
        self.params = params if params else ini_params  # 如果提供了参数则使用提供的参数，否则使用默认参数

    def load_model(self, model_path):  # 定义加载模型的方法
        self.device = select_device(self.params['device'])  # 选择设备
        # print(os.path.basename(model_path)[:3])
        if os.path.basename(model_path)[:3] == 'seg':
            task = 'segment'
        else:
            task = 'detect'
        self.model = YOLO(model_path, task=task)
        names_dict = self.model.names  # 获取类别名称字典

        self.names = [names_dict[i] for i in range(len(names_dict))]  # 默认使用所有类别名称

        self.model(torch.zeros(1, 3, *[self.imgsz] * 2).to(self.device).
                   type_as(next(self.model.model.parameters())))  # 预热

    def preprocess(self, img):  # 定义预处理方法
        self.img = img  # 保存原始图像
        return img  # 返回处理后的图像

    def predict(self, img):  # 定义预测方法
        results = self.model(img, **ini_params)
        return results

    def postprocess(self, pred):
        results = []
        if not pred or not pred[0].boxes:
            return results

        has_masks = pred[0].masks is not None

        def is_valid_mask(mask_xy, class_id):
            if not (mask_xy and isinstance(mask_xy, list)):
                print(f"[警告] 类别 {self.names[class_id]} (ID:{class_id}) 的掩码不是列表或为空")
                return False
            first_contour = mask_xy[0]
            if not (isinstance(first_contour, np.ndarray) and first_contour.ndim == 2 and first_contour.shape[1] == 2):
                print(f"[警告] 类别 {self.names[class_id]} (ID:{class_id}) 掩码格式异常: {getattr(first_contour, 'shape', None)}")
                return False
            if first_contour.size == 0:
                print(f"[警告] 类别 {self.names[class_id]} (ID:{class_id}) 的掩码轮廓为空")
                return False
            return True

        for aim_id, box in enumerate(pred[0].boxes):
            class_id = int(box.cls.cpu())
            bbox = [int(coord) for coord in box.xyxy.cpu().squeeze().tolist()]

            mask_data = None
            if has_masks and aim_id < len(pred[0].masks):
                try:
                    mask_xy = pred[0].masks[aim_id].xy
                    if is_valid_mask(mask_xy, class_id):
                        mask_data = mask_xy
                except Exception as e:
                    print(f"[错误] 处理类别 {self.names[class_id]} (ID:{class_id}) 掩码时出现异常: {e}")

            results.append({
                "class_name": self.names[class_id],
                "bbox": bbox,
                "score": box.conf.cpu().squeeze().item(),
                "class_id": class_id,
                "mask": mask_data
            })

        return results

    def set_param(self, params):
        self.params.update(params)
