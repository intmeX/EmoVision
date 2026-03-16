# EmoVision Agent Guidelines

Visual emotion recognition web app with real-time pipeline for images, videos, and camera feeds.

**Stack:** FastAPI + WebSocket + YOLO11 + PyTorch | React 18 + TypeScript + Vite + Tailwind + Zustand

## Build Commands
```bash
# Backend (from backend/)
pip install -r requirements.txt           # Install deps
uvicorn app.main:app --reload --port 8000 # Dev server
ruff check . && ruff format .             # Lint + format

# Frontend (from frontend/)
npm install                               # Install deps
npm run dev                               # Dev server
npm run lint                              # ESLint
```

## Testing
```bash
# Backend
pytest tests/ -v
pytest tests/ --cov=app --cov-report=term-missing

# Frontend
cd frontend && npx tsc --noEmit
```

## Code Style
- **Python:** Ruff (line-length: 88, py310). `snake_case` (funcs/vars), `PascalCase` (classes). Required types.
- **TypeScript:** Strict mode. `@/*` aliases. `PascalCase` (components), `camelCase` (funcs/vars). Functional only.
- **State:** Zustand in `store/`.

## Non-Standard Patterns
- **Static Assets:** `backend/app/assets/` contains static fonts.
- **Model Weights:** Utilities in `backend/models/`, weights (`.pth`, `.pt`) at root.
- **Uploads:** `backend/uploads/` is at root level.
- **Dead Folders:** `frontend/src/components/common/` is empty.

## Critical Patterns

### Async Frame Processing (Backend)
```python
# Use ThreadPoolExecutor for CPU-bound OpenCV/ML tasks
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(self._executor, self._sync_function, args)
```

### Source Switching - Clear Buffers (Backend)
```python
# source_manager.close() MUST clear frame queue
self._frame_queue.clear()
# pipeline.stop() MUST cancel pending encode tasks
if self._pending_encode:
    self._pending_encode.cancel()
```

### Binary WebSocket Protocol
```python
# Backend: Send JSON header, then binary JPEG
await conn.send_text(header.model_dump_json())
await conn.send_bytes(image_bytes)

// Frontend: Receive header, then blob
const imageUrl = URL.createObjectURL(blob);
```

### Canvas Rendering (Frontend)
```typescript
// Canvas MUST be in DOM. Use hidden class, NOT conditional render.
<canvas className={isRunning ? '' : 'hidden'} />

// Efficient decoding
const bitmap = await createImageBitmap(blob);
ctx.drawImage(bitmap, 0, 0, width, height);
bitmap.close();
URL.revokeObjectURL(url);
```
