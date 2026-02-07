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
npm run dev                               # Dev server (port 5173)
npm run build                             # Production build
npm run lint                              # ESLint (zero warnings)
```

## Testing

```bash
# Backend - pytest
cd backend
pytest tests/ -v                                                              # All tests
pytest tests/test_pipeline.py -v                                              # Single file
pytest tests/test_pipeline.py::TestPipeline::test_pipeline_initialization -v  # Single test
pytest tests/ --cov=app --cov-report=term-missing                             # Coverage

# Frontend - TypeScript check
cd frontend && npx tsc --noEmit
```

## Code Style

### Python
- **Formatter:** Ruff (line-length: 88, target: py310)
- **Imports:** stdlib → third-party → local (separated by blank lines)
- **Naming:** `snake_case` (funcs/vars), `PascalCase` (classes), `UPPER_CASE` (constants)
- **Types:** Required for all public functions
- **Docstrings:** `"""Args/Returns/Raises"""`

### TypeScript/React
- **Mode:** Strict (`noUnusedLocals`, `noUnusedParameters`)
- **Imports:** Use `@/*` path alias for src imports
- **Naming:** `PascalCase` (components/types), `camelCase` (funcs/vars)
- **Components:** Functional only, one per file
- **State:** Zustand stores in `store/` directory

## Project Structure

```
backend/app/
  api/        # Routes, dependencies
  core/       # Pipeline, SourceManager, SessionManager
  modules/    # detector/, recognizer/, visualizer/
  schemas/    # Pydantic models
  utils/      # Logger, device utils, frame_utils

frontend/src/
  components/ # UI components (video/, config/, dashboard/)
  hooks/      # useWebSocket, useFrame, usePipeline
  store/      # Zustand stores (pipelineStore, configStore)
  services/   # API, WebSocket, frameManager, frameBuffer
  types/      # TypeScript definitions
```

## Critical Patterns

### Async Frame Processing (Backend)
```python
# Use ThreadPoolExecutor for CPU-bound OpenCV/ML tasks
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(self._executor, self._sync_function, args)
```

### Source Switching - Clear All Buffers (Backend)
```python
# In source_manager.close() - MUST clear frame queue to prevent stale frames
self._frame_queue.clear()

# In pipeline.stop() - MUST cancel pending encode tasks
if self._pending_encode is not None:
    self._pending_encode.cancel()
```

### Binary WebSocket Protocol
```python
# Backend: Send JSON header first, then binary JPEG bytes
await conn.send_text(header.model_dump_json())
await conn.send_bytes(image_bytes)

# Frontend: Receive header, then blob, create Object URL
const imageUrl = URL.createObjectURL(blob);
```

### Canvas Rendering (Frontend)
```typescript
// Canvas MUST always be in DOM - use hidden class, NOT conditional render
<canvas className={isRunning ? '' : 'hidden'} />

// Use createImageBitmap for efficient decoding
const bitmap = await createImageBitmap(blob);
ctx.drawImage(bitmap, 0, 0, width, height);
bitmap.close();
URL.revokeObjectURL(url);  // Clean up Object URLs
```

## DO NOT
- Use `any`, `@ts-ignore`, `as any` in TypeScript
- Block event loop with sync I/O (use `run_in_executor`)
- Conditionally render Canvas (breaks ref binding)
- Forget to clear `_frame_queue` when switching sources
- Hardcode secrets - use environment variables

## DO
- Run `ruff check` / `npm run lint` before commits
- Clear all frame buffers when switching visual sources
- Cancel pending async tasks in `stop()` methods
- Handle WebSocket disconnection gracefully
- Use `createImageBitmap` + `bitmap.close()` for frames

---

# EmoVision 代理开发指南

视觉情绪识别 Web 应用，支持图像、视频和摄像头的实时处理流水线。

**技术栈:** FastAPI + WebSocket + YOLO11 + PyTorch | React 18 + TypeScript + Vite + Tailwind + Zustand

## 构建命令

```bash
# 后端 (backend/ 目录)
pip install -r requirements.txt           # 安装依赖
uvicorn app.main:app --reload --port 8000 # 开发服务器
ruff check . && ruff format .             # 代码检查

# 前端 (frontend/ 目录)
npm install && npm run dev                # 安装并启动
npm run build                             # 生产构建
npm run lint                              # ESLint 检查
```

## 测试命令

```bash
# 后端
pytest tests/ -v                                                              # 全部测试
pytest tests/test_pipeline.py::TestPipeline::test_pipeline_initialization -v  # 单个测试

# 前端类型检查
cd frontend && npx tsc --noEmit
```

## 代码规范

### Python
- **格式化:** Ruff (行长 88, Python 3.10+)
- **导入顺序:** 标准库 → 第三方 → 本地
- **命名:** `snake_case` (函数/变量), `PascalCase` (类)
- **类型注解:** 公共函数必须

### TypeScript/React
- **严格模式:** 启用 `noUnusedLocals`, `noUnusedParameters`
- **路径别名:** 使用 `@/*` 导入 src 目录
- **组件:** 仅函数式组件，每文件一个

## 关键模式

### 异步帧处理 (后端)
```python
# 使用线程池执行 CPU 密集任务，避免阻塞事件循环
result = await loop.run_in_executor(self._executor, sync_func, args)
```

### 视觉源切换 - 清除所有缓冲区 (后端)
```python
# source_manager.close() 中必须清除帧队列
self._frame_queue.clear()

# pipeline.stop() 中必须取消待处理的编码任务
if self._pending_encode is not None:
    self._pending_encode.cancel()
```

### 二进制 WebSocket 协议
```python
# 后端：先发 JSON 头部，再发二进制图像
await conn.send_text(header_json)
await conn.send_bytes(image_bytes)
```

### Canvas 渲染 (前端)
```typescript
// Canvas 必须始终在 DOM 中，用 hidden 控制显示，不要条件渲染
<canvas className={isRunning ? '' : 'hidden'} />

// 使用 createImageBitmap 高效解码
const bitmap = await createImageBitmap(blob);
ctx.drawImage(bitmap, 0, 0, width, height);
bitmap.close();
```

## 禁止事项
- TypeScript 中使用 `any`、`@ts-ignore`
- 在异步处理器中阻塞事件循环
- 条件渲染 Canvas（会破坏 ref 绑定）
- 切换视觉源时忘记清除 `_frame_queue`
- 硬编码密钥

## 推荐做法
- 提交前运行 `ruff check` / `npm run lint`
- 切换视觉源时清除所有帧缓冲区
- 在 `stop()` 方法中取消待处理的异步任务
- 优雅处理 WebSocket 断连
- 使用 `createImageBitmap` + `bitmap.close()` 处理帧
