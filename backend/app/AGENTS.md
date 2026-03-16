# Backend Application

FastAPI application with API routes, core pipeline, and processing modules.

## Structure
```
app/
├── api/           # API layer (routes, dependencies, controller)
├── core/          # Core business logic (pipeline, session, source manager)
├── modules/       # Processing modules (see modules/AGENTS.md)
├── schemas/       # Pydantic models
├── utils/         # Utilities (logger, device, frame utils)
├── assets/        # Static assets (fonts)
├── config.py      # Application configuration
└── main.py        # FastAPI app entry point
```

## Where to Look

| Task | Location |
|------|----------|
| Add API endpoint | `api/routes/` |
| Modify pipeline | `core/pipeline.py` |
| Session management | `core/session.py` |
| Source switching | `core/source_manager.py` |
| Request/response models | `schemas/` |
| Logging | `utils/logger.py` |
| Device detection | `utils/device.py` |

## Key Files

- `main.py` — FastAPI app, CORS, route registration, uvicorn entry
- `api/pipeline_controller.py` — Singleton pipeline controller
- `api/routes/pipeline.py` — Pipeline control endpoints (start/stop/configure)
- `api/routes/source.py` — Source upload/selection endpoints
- `api/routes/websocket.py` — WebSocket frame streaming
- `core/pipeline.py` — Frame processing orchestration
- `core/session.py` — Session state management
- `core/source_manager.py` — Video/image/camera source handling

## Conventions

- **API Routes**: Grouped by feature in `api/routes/`
- **Dependencies**: Shared dependencies in `api/deps.py`
- **Schemas**: Pydantic v2 models in `schemas/`
- **Async**: All route handlers are async
- **Error Handling**: HTTPException for API errors, log for internal errors

## Critical

**Pipeline Lifecycle**
```python
# Start: configure → load models → start source → begin processing
await pipeline.start(source_config, module_configs)

# Stop: cancel tasks → close source → clear buffers
await pipeline.stop()
```

**Source Manager**
```python
# MUST clear frame queue on close
def close(self):
    self._frame_queue.clear()  # Prevent stale frames
```

**WebSocket Streaming**
```python
# Binary protocol: JSON header + JPEG bytes
await websocket.send_text(header_json)
await websocket.send_bytes(jpeg_bytes)
```

## Notes

- `assets/fonts/` contains NotoSansSC-Regular.ttf for Chinese text rendering
- Pipeline controller is singleton (one pipeline per app instance)
- WebSocket connection is 1:1 with pipeline (no multi-client support)
