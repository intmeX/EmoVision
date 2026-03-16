# Processing Modules

Pluggable detector, recognizer, and visualizer modules.

## Structure
```
modules/
├── detector/      # Face/body detection (YOLO11)
├── recognizer/    # Emotion recognition (multiple models)
├── visualizer/    # Frame rendering with bounding boxes
└── base.py        # Base module interface
```

## Where to Look

| Task | Location |
|------|----------|
| Add detector | `detector/` - inherit `BaseDetector` |
| Add recognizer | `recognizer/` - inherit `BaseEmotionRecognizer` |
| Change visualization | `visualizer/frame_renderer.py` |
| Define detection schema | `detector/schemas.py` |
| Define emotion schema | `recognizer/schemas.py` |

## Module Pattern

All modules inherit from `BaseModule` and implement:
- `configure(config)` — Update module settings
- `process(frame, ...)` — Main processing logic (sync or async)

**Detector**: `YOLODetector` wraps ultralytics YOLO11
**Recognizer**: Multiple implementations (CAER, DDEN, Emotic, Mock)
**Visualizer**: `FrameRenderer` draws boxes/labels with OpenCV

## Conventions

- **Sync Processing**: CPU-bound work (OpenCV, ML inference) runs in executor
- **Schemas**: Each module has `schemas.py` for config/output models
- **Model Loading**: Lazy load in `configure()`, not `__init__()`
- **Error Handling**: Return empty results on failure, log errors

## Critical

**Recognizer Matching**
```python
# Match detections to recognitions by IoU
from app.modules.recognizer.matching import match_detections_to_emotions
```

**Preprocessing**
```python
# Use module-specific preprocessing
from app.modules.recognizer.preprocessing import preprocess_for_caer
```
