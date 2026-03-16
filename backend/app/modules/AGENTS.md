# ML Processing Modules

Core ML processing nodes for the EmoVision pipeline.

## Structure
- `detector/`: Face and body detection models (YOLO11).
- `recognizer/`: Emotion recognition implementations.
- `visualizer/`: Frame rendering with bounding boxes and labels.

## Device Management
- Use `app/utils/device.py` for CPU/GPU detection and tensor movements.
- Never hardcode "cuda" or "cpu" in module logic.

## Processing Pattern
- Wrap CPU/GPU-bound tasks with `run_in_background` or `run_in_executor` to prevent event loop blocking.

## Development Rules
- Keep ML logic separated by domain (detection vs recognition).
- Subclass base interfaces for new model integrations.
- Fail gracefully on inference errors; return empty results instead of crashing the pipeline.
- Initialize models lazily during configuration, not in `__init__`.
