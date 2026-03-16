# Backend Knowledge Base

FastAPI + WebSocket + YOLO11 + PyTorch emotion recognition backend.

## Structure
```
backend/
├── app/           # Application code (see app/AGENTS.md)
├── models/        # Model architecture definitions (Python)
├── tests/         # pytest test suite
├── uploads/       # User-uploaded media files
├── *.pt, *.pth    # Model weights (non-standard: should be in models/)
└── requirements.txt
```

## Where to Look

| Task | Location | Notes |
|------|----------|-------|
| Start server | `app/main.py` | Entry point, uvicorn target |
| Add API route | `app/api/routes/` | REST + WebSocket endpoints |
| Modify pipeline | `app/core/pipeline.py` | Frame processing orchestration |
| Add detector | `app/modules/detector/` | Inherit `BaseDetector` |
| Add recognizer | `app/modules/recognizer/` | Inherit `BaseEmotionRecognizer` |
| Change visualization | `app/modules/visualizer/` | Frame rendering logic |
| Add tests | `tests/` | pytest, `test_*.py` naming |

## Commands

```bash
# Setup
pip install -r requirements.txt

# Dev server (port 8000)
uvicorn app.main:app --reload

# Testing
pytest tests/ -v                          # All tests
pytest tests/test_pipeline.py -v         # Single file
pytest tests/ --cov=app --cov-report=term-missing  # Coverage

# Linting
ruff check .                              # Check
ruff format .                             # Format
```

## Conventions

- **Ruff**: line-length 88, target py310, ignores E501
- **Imports**: stdlib → third-party → local (blank line separated)
- **Naming**: `snake_case` (funcs/vars), `PascalCase` (classes), `UPPER_CASE` (constants)
- **Types**: Required for all public functions
- **Async**: Use `loop.run_in_executor()` for CPU-bound tasks (OpenCV, ML inference)

## Critical Patterns

**Async Frame Processing**
```python
# MUST use ThreadPoolExecutor for CPU-bound tasks
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(self._executor, sync_func, args)
```

**Source Switching**
```python
# In source_manager.close() - MUST clear frame queue
self._frame_queue.clear()

# In pipeline.stop() - MUST cancel pending encode tasks
if self._pending_encode is not None:
    self._pending_encode.cancel()
```

**WebSocket Protocol**
```python
# Send JSON header first, then binary JPEG
await conn.send_text(header.model_dump_json())
await conn.send_bytes(image_bytes)
```

## Anti-Patterns

- Block event loop with sync I/O (use `run_in_executor`)
- Forget to clear `_frame_queue` on source switch
- Skip cancelling pending tasks in `stop()` methods
- Hardcode secrets (use environment variables)

## Notes

- Model weights (*.pt, *.pth) are in backend root (non-standard, should be in `models/weights/`)
- `uploads/` directory stores user-uploaded images/videos
- WebSocket sends binary frames (JSON header + JPEG bytes)
