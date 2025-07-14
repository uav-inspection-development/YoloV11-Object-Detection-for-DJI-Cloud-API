import numpy as np
from src.utils import compute_missing_panels


def test_compute_missing_panels_basic():
    detections = [
        {"class_name": "string", "bbox": [0, 0, 100, 100], "score": 1.0, "class_id": 0},
        {"class_name": "component", "bbox": [0, 0, 50, 100], "score": 1.0, "class_id": 1},
    ]
    missing = compute_missing_panels(detections, (100, 100, 3), min_area=10)
    assert len(missing) == 1
    m_bbox = missing[0]["bbox"]
    assert m_bbox == [50, 0, 100, 100]
