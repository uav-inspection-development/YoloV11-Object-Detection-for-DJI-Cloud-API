import cv2
import numpy as np
# 修复NumPy 2.x与imgaug的兼容性问题
# NumPy 2.0移除了np.sctypes，imgaug仍在使用它
if not hasattr(np, 'sctypes'):
    # 重新创建imgaug所需的sctypes结构
    np.sctypes = {
        'int': [np.int8, np.int16, np.int32, np.int64],
        'uint': [np.uint8, np.uint16, np.uint32, np.uint64],
        'float': [np.float16, np.float32, np.float64],
        'complex': [np.complex64, np.complex128],
        'others': [bool, object, str]
    }

import imgaug as ia
import imgaug.augmenters as iaa
from imgaug.augmentables.bbs import BoundingBox, BoundingBoxesOnImage
import yaml
import shutil
from pathlib import Path
import argparse
from tqdm import tqdm


class YOLODataAugmenter:
    def __init__(self, dataset_path, output_path=None):
        """
        初始化YOLO数据增广器
        
        Args:
            dataset_path: 数据集根目录路径
            output_path: 输出路径，如果为None则在原数据集目录同级创建augmented文件夹
        """
        # 定义数据增广变换序列 - 针对红外灰阶无人机图像优化
        self.augmentation_list = [
            # 0. 水平翻转 (适合无人机航拍)
            iaa.Fliplr(1.0),
            
            # 1. 垂直翻转 (模拟不同飞行方向)
            iaa.Flipud(1.0),
            
            # 2. 小角度旋转 (模拟无人机姿态变化)
            iaa.Rotate((-15, 15)),
            
            # 3. 大角度旋转 (模拟无人机不同方向拍摄)
            iaa.Rotate((-45, 45)),
            
            # 4. 仿射变换 (模拟无人机位置变化和透视)
            iaa.Affine(
                scale={"x": (0.8, 1.2), "y": (0.8, 1.2)},  # 缩放
                translate_percent={"x": (-0.1, 0.1), "y": (-0.1, 0.1)},  # 平移
                rotate=(-10, 10),  # 小角度旋转
                shear=(-8, 8),  # 剪切变换
                mode='edge'  # 边缘填充模式
            ),
            
            # 5. 透视变换 (模拟不同高度和角度的航拍)
            iaa.PerspectiveTransform(scale=(0.05, 0.15)),
            
            # 6. 弹性变形 (模拟轻微的图像畸变)
            iaa.ElasticTransformation(alpha=(0, 30), sigma=5),
            
            # 7. 红外图像特定的亮度调整 (模拟不同温度环境)
            iaa.Sequential([
                iaa.Multiply((0.6, 1.4)),  # 更大范围的亮度调整
                iaa.Add((-40, 40))  # 添加偏移值模拟环境温度变化
            ]),
            
            # 8. 对比度和伽马调整 (增强红外图像细节)
            iaa.Sequential([
                iaa.LinearContrast((0.6, 1.4)),  # 对比度调整
                iaa.GammaContrast((0.7, 1.3))  # 伽马校正
            ]),
            
            # 9. 高斯噪声 (模拟传感器噪声)
            iaa.AdditiveGaussianNoise(scale=(0, 0.05*255)),
            
            # 10. 高斯模糊 (模拟运动模糊或焦点问题)
            iaa.GaussianBlur(sigma=(0.5, 1.5)),
            
            # 11. 复合变换：几何+亮度 (模拟真实拍摄条件)
            iaa.Sequential([
                iaa.Affine(
                    scale=(0.9, 1.1),
                    rotate=(-20, 20),
                    translate_percent=(-0.05, 0.05)
                ),
                iaa.Multiply((0.8, 1.2)),
                iaa.LinearContrast((0.9, 1.1))
            ]),
            
            # 12. 梯形变换 (模拟倾斜角度拍摄)
            # time consuning, 14s on a single image
            # iaa.Sequential([
            #     iaa.PiecewiseAffine(scale=(0.01, 0.05)),
            #     iaa.Multiply((0.9, 1.1))
            # ]),
            
            # 13. 复合几何变换：旋转+透视 (模拟复杂飞行姿态)
            iaa.Sequential([
                iaa.Rotate((-30, 30)),
                iaa.PerspectiveTransform(scale=(0.08, 0.12)),
                iaa.Multiply((0.85, 1.15))
            ]),
            
            # 14. 非均匀缩放 (模拟不同距离拍摄)
            iaa.Affine(
                scale={"x": (0.7, 1.3), "y": (0.7, 1.3)},
                mode='reflect'
            ),
            
            # 15. 桶形/枕形畸变 (模拟镜头畸变)
            # time consuning, 14s on a single image
            # iaa.Sequential([
            #     iaa.PiecewiseAffine(scale=(0.02, 0.08)),
            #     iaa.LinearContrast((0.8, 1.2))
            # ]),
            
            # 16. 红外热像仪特定噪声组合
            iaa.Sequential([
                iaa.AdditiveGaussianNoise(scale=(0, 0.08*255)),
                iaa.AdditiveLaplaceNoise(scale=(0, 0.03*255)),
                iaa.Multiply((0.7, 1.3))
            ]),
            
            # 17. 大角度旋转+剪切 (模拟极端飞行角度)
            iaa.Sequential([
                iaa.Rotate((-60, 60)),
                iaa.Affine(shear=(-15, 15)),
                iaa.Multiply((0.8, 1.2))
            ]),
            
            # 18. 弹性变形+亮度梯度 (模拟大气折射效应)
            iaa.Sequential([
                iaa.ElasticTransformation(alpha=(10, 50), sigma=(3, 7)),
                iaa.Add((-50, 50)),
                iaa.LinearContrast((0.7, 1.3))
            ]),
            
            # 19. 多层次透视变换 (模拟复杂地形航拍)
            iaa.Sequential([
                iaa.PerspectiveTransform(scale=(0.1, 0.2)),
                iaa.Affine(translate_percent=(-0.15, 0.15)),
                iaa.GammaContrast((0.6, 1.4))
            ]),
            
            # 20. 热噪声+对比度增强 (模拟恶劣环境)
            iaa.Sequential([
                iaa.AdditiveGaussianNoise(scale=(0, 0.1*255)),
                iaa.SigmoidContrast(gain=(5, 15), cutoff=(0.3, 0.7)),
                iaa.Add((-30, 30))
            ]),
            
            # 21. 复合旋转+缩放+平移 (模拟动态飞行)
            iaa.Sequential([
                iaa.Affine(
                    scale=(0.6, 1.4),
                    rotate=(-50, 50),
                    translate_percent=(-0.2, 0.2),
                    shear=(-10, 10)
                ),
                iaa.Multiply((0.75, 1.25))
            ]),
            
            # 22. 超大角度旋转+翻转组合 (模拟全方向拍摄)
            iaa.Sequential([
                iaa.Sometimes(0.5, iaa.Fliplr(1.0)),
                iaa.Sometimes(0.5, iaa.Flipud(1.0)),
                iaa.Rotate((-90, 90)),
                iaa.LinearContrast((0.6, 1.4))
            ])
        ]
        
        
        self.dataset_path = Path(dataset_path)
        if output_path:
            self.output_path = Path(output_path)
        else:
            # 在原数据集文件夹名称后面添加 _augmented
            self.output_path = self.dataset_path.parent / (self.dataset_path.name + "_augmented")
        
        # 读取数据集配置
        with open(self.dataset_path / "data.yaml", 'r') as f:
            self.config = yaml.safe_load(f)
        
        # 创建输出目录结构
        self.setup_output_dirs()
    
    def setup_output_dirs(self):
        """创建输出目录结构"""
        for split in ['train', 'val', 'test']:
            # 创建图片目录
            img_dir = self.output_path / "images" / split
            img_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建标签目录
            label_dir = self.output_path / "labels" / split
            label_dir.mkdir(parents=True, exist_ok=True)
    
    def yolo_to_imgaug_bbox(self, yolo_bbox, img_width, img_height):
        """
        将YOLO格式的边界框转换为imgaug格式
        
        Args:
            yolo_bbox: [class_id, center_x, center_y, width, height] (归一化坐标)
            img_width: 图片宽度
            img_height: 图片高度
        
        Returns:
            BoundingBox对象
        """
        class_id, center_x, center_y, width, height = yolo_bbox
        
        # 转换为绝对坐标
        center_x_abs = center_x * img_width
        center_y_abs = center_y * img_height
        width_abs = width * img_width
        height_abs = height * img_height
        
        # 计算左上角和右下角坐标
        x1 = center_x_abs - width_abs / 2
        y1 = center_y_abs - height_abs / 2
        x2 = center_x_abs + width_abs / 2
        y2 = center_y_abs + height_abs / 2
        
        return BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2, label=int(class_id))
    
    def imgaug_to_yolo_bbox(self, bbox, img_width, img_height):
        """
        将imgaug格式的边界框转换为YOLO格式
        
        Args:
            bbox: BoundingBox对象
            img_width: 图片宽度
            img_height: 图片高度
        
        Returns:
            [class_id, center_x, center_y, width, height] (归一化坐标)
        """
        # 获取边界框坐标
        x1, y1, x2, y2 = bbox.x1, bbox.y1, bbox.x2, bbox.y2
        
        # 计算中心点和宽高
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        width = x2 - x1
        height = y2 - y1
        
        # 归一化
        center_x_norm = center_x / img_width
        center_y_norm = center_y / img_height
        width_norm = width / img_width
        height_norm = height / img_height
        
        return [bbox.label, center_x_norm, center_y_norm, width_norm, height_norm]
    
    def load_yolo_annotations(self, label_file):
        """加载YOLO格式的标注文件"""
        annotations = []
        if label_file.exists():
            with open(label_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        parts = line.split()
                        class_id = int(parts[0])
                        coords = [float(x) for x in parts[1:]]
                        annotations.append([class_id] + coords)
        return annotations
    
    def save_yolo_annotations(self, annotations, output_file):
        """保存YOLO格式的标注文件"""
        with open(output_file, 'w') as f:
            for ann in annotations:
                class_id = int(ann[0])
                coords = ann[1:]
                line = f"{class_id} " + " ".join([f"{x:.6f}" for x in coords])
                f.write(line + "\n")
    
    def augment_image_and_bbox(self, image, bboxes_on_image, augmenter):
        """对图像和边界框进行增广"""
        try:
            # 应用增广
            image_aug, bboxes_aug = augmenter(image=image, bounding_boxes=bboxes_on_image)
            
            # 过滤掉超出图像边界或面积过小的边界框
            bboxes_filtered = []
            for bbox in bboxes_aug.bounding_boxes:
                # 确保边界框在图像范围内
                if (bbox.x1 >= 0 and bbox.y1 >= 0 and 
                    bbox.x2 <= image_aug.shape[1] and bbox.y2 <= image_aug.shape[0] and
                    bbox.x2 > bbox.x1 and bbox.y2 > bbox.y1):
                    # 检查边界框面积
                    area = (bbox.x2 - bbox.x1) * (bbox.y2 - bbox.y1)
                    if area > 100:  # 最小面积阈值
                        bboxes_filtered.append(bbox)
            
            bboxes_filtered_on_image = BoundingBoxesOnImage(bboxes_filtered, shape=image_aug.shape)
            return image_aug, bboxes_filtered_on_image
            
        except Exception as e:
            print(f"Error during augmentation: {e}")
            return None, None
    
    def process_split(self, split_name):
        """处理指定的数据集分割"""
        print(f"Processing {split_name} split...")
        
        # 获取原始图片和标签目录
        img_dir = self.dataset_path / "images" / split_name
        label_dir = self.dataset_path / "labels" / split_name
        
        # 获取输出目录
        output_img_dir = self.output_path / "images" / split_name
        output_label_dir = self.output_path / "labels" / split_name
        
        if not img_dir.exists():
            print(f"Image directory {img_dir} does not exist, skipping...")
            return
        
        # 获取所有图片文件
        image_files = list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.jpeg")) + list(img_dir.glob("*.png"))
        
        augmented_count = 0
        
        for img_file in tqdm(image_files, desc=f"处理{split_name}集", unit="张"):
            try:
                # 读取图片
                image = cv2.imread(str(img_file))
                if image is None:
                    print(f"Warning: Could not read image {img_file}")
                    continue
                    
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                img_height, img_width = image_rgb.shape[:2]
                
                # 读取对应的标注文件
                label_file = label_dir / f"{img_file.stem}.txt"
                annotations = self.load_yolo_annotations(label_file)
                
                # 将YOLO格式转换为imgaug格式
                bboxes = []
                for ann in annotations:
                    bbox = self.yolo_to_imgaug_bbox(ann, img_width, img_height)
                    bboxes.append(bbox)
                
                bboxes_on_image = BoundingBoxesOnImage(bboxes, shape=image_rgb.shape)
                
                # 随机选择5个变换索引
                # selected_indices = random.sample(range(len(self.augmentation_list)), 5)
                # selected_indices = [10]
                #  time consuming augmentation: 6,9

                # 应用每个变换
                for i, augmenter in enumerate(self.augmentation_list):
                    # if i not in selected_indices:
                    #     continue

                    aug_image, aug_bboxes = self.augment_image_and_bbox(
                        image_rgb, bboxes_on_image, augmenter
                    )
                    
                    if aug_image is not None and aug_bboxes is not None:
                        # 生成输出文件名
                        output_img_name = f"{img_file.stem}_aug_{i}{img_file.suffix}"
                        output_label_name = f"{img_file.stem}_aug_{i}.txt"
                        
                        # 保存增广后的图片
                        output_img_path = output_img_dir / output_img_name
                        aug_image_bgr = cv2.cvtColor(aug_image, cv2.COLOR_RGB2BGR)
                        cv2.imwrite(str(output_img_path), aug_image_bgr)
                        
                        # 转换边界框格式并保存标注
                        aug_annotations = []
                        for bbox in aug_bboxes.bounding_boxes:
                            yolo_bbox = self.imgaug_to_yolo_bbox(
                                bbox, aug_image.shape[1], aug_image.shape[0]
                            )
                            aug_annotations.append(yolo_bbox)
                        
                        output_label_path = output_label_dir / output_label_name
                        self.save_yolo_annotations(aug_annotations, output_label_path)
                        
                        augmented_count += 1
                
                # 复制原始文件到输出目录
                shutil.copy2(img_file, output_img_dir / img_file.name)
                if label_file.exists():
                    shutil.copy2(label_file, output_label_dir / label_file.name)
                    
            except Exception as e:
                print(f"Error processing {img_file}: {e}")
                continue
        
        print(f"Generated {augmented_count} augmented images for {split_name} split")
    
    def create_augmented_config(self):
        """创建增广数据集的配置文件"""
        # 复制原始配置
        aug_config = self.config.copy()
        
        # 更新路径
        aug_config['train'] = './images/train'
        aug_config['val'] = './images/val'
        if 'test' in aug_config:
            aug_config['test'] = './images/test'
        
        # 保存配置文件
        config_path = self.output_path / "EL_data_augmented.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(aug_config, f, default_flow_style=False)
        
        print(f"Augmented dataset configuration saved to {config_path}")
    
    def run_augmentation(self, splits=['train']):
        """运行数据增广"""
        print("Starting data augmentation...")
        print(f"Dataset path: {self.dataset_path}")
        print(f"Output path: {self.output_path}")
        print(f"Augmentation transforms: {len(self.augmentation_list)}")
        
        for split in splits:
            self.process_split(split)
        
        # 创建增广数据集配置文件
        self.create_augmented_config()
        
        print("Data augmentation completed!")


def main():
    parser = argparse.ArgumentParser(description="YOLO 数据增强脚本")
    parser.add_argument("--dataset_path", required=True, help="数据集根目录路径（如 D:/data/EL_data ）")
    parser.add_argument("--output_path", default=None, help="输出路径（如 D:/data/EL_data_augmented ，默认在原数据集目录同级创建augmented文件夹）")
    parser.add_argument("--splits", default="train,val,test", help="需要增广的数据集分割，多个用英文逗号分隔，默认增广全部  ，可选: train,val,test")
    args = parser.parse_args()

    dataset_path = args.dataset_path
    output_path = args.output_path
    splits_input = args.splits

    # 解析 splits
    split_options = ['train', 'val', 'test']
    splits = [s.strip() for s in splits_input.split(',') if s.strip() in split_options]
    if not splits:
        print("输入无效，默认只增广train。")
        splits = ['train']

    print(f"[*] 数据集路径: {dataset_path}")
    print(f"[*] 选择的分割: {splits}")

    # 创建数据增广器
    augmenter = YOLODataAugmenter(dataset_path, output_path=output_path)

    # 运行增广
    augmenter.run_augmentation(splits=splits)


if __name__ == "__main__":
    main()