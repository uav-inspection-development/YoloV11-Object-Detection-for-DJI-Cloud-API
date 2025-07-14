import numpy as np
from src.utils import compute_misaligned_panels


def test_compute_misaligned_panels_basic():
    detections = [
        {"class_name": "string", "bbox": [0, 0, 200, 100], "score": 1.0, "class_id": 0},
        {
            "class_name": "component",
            "bbox": [0, 0, 50, 100],
            "score": 1.0,
            "class_id": 1,
            "mask": np.array([[0, 0], [50, 0], [50, 100], [0, 100]]),
        },
        {
            "class_name": "component",
            "bbox": [60, 0, 110, 100],
            "score": 1.0,
            "class_id": 2,
            "mask": np.array([[60, 0], [110, 10], [100, 100], [50, 90]]),
        },
    ]

    misaligned = compute_misaligned_panels(detections, angle_threshold=5, center_ratio=0.1)
    assert any(det["class_name"] == "misaligned_panel" for det in misaligned)

