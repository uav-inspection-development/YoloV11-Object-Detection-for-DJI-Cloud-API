# utils_data 文件夹说明

utils_data文件夹中的脚本主要用于处理数据集，包括数据集的转换、增强和可视化等功能。所有的脚本参数都支持通过argparse进行设置。

以下是该文件夹中脚本的简要说明：

- `util_dataset_augmentation.py`: 数据集增广
- `util_dataset_get_label_name.py`: 获取数据集全部类别名称
- `util_dataset_manipulation.py`: YOLO数据集处理
- `util_encryption.py`: 代码加密
- `util_image_visualization_datection.py`: YOLO检测数据集绘制标注框
- `util_image_visualization_segmentation.py`: YOLO分割数据集绘制标注框
- `util_via_to_yolo_conversion.py`: VIA（VGG Image Annotator）转YOLO数据集
- `util_voc_to_yolo_conversion.py`: VOC（Pascal VOC）转YOLO数据集
