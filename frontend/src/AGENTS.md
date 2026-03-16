# Frontend Source

React application structure with hooks, stores, and services.

## Structure
```
src/
├── components/    # UI components (see components/AGENTS.md)
├── hooks/         # Custom React hooks
├── store/         # Zustand state management
├── services/      # API, WebSocket, frame management
├── types/         # TypeScript definitions
├── styles/        # Global CSS
├── utils/         # Helper functions
├── main.tsx       # React entry point
└── App.tsx        # Root component
```

## Where to Look

| Task | Location |
|------|----------|
| Add UI component | `components/` |
| Add custom hook | `hooks/` |
| Modify state | `store/` |
| API integration | `services/api.ts` |
| WebSocket logic | `services/websocket.ts` |
| Frame buffering | `services/frameBuffer.ts` |
| Type definitions | `types/` |

## Key Files

- `main.tsx` — ReactDOM.createRoot, renders `<App />`
- `App.tsx` — Root component, layout, WebSocket initialization
- `hooks/useWebSocket.ts` — WebSocket connection management
- `hooks/useFrame.ts` — Frame rendering to canvas
- `hooks/usePipeline.ts` — Pipeline control (start/stop/configure)
- `store/pipelineStore.ts` — Pipeline state (running, FPS, latency)
- `store/configStore.ts` — Configuration state (detector, recognizer, visualizer)
- `services/frameManager.ts` — Frame queue management
- `services/frameBuffer.ts` — Circular buffer for frame history

## Conventions

- **Hooks**: Prefix with `use`, one responsibility per hook
- **Stores**: Zustand with immer middleware for immutable updates
- **Services**: Pure functions or classes, no React dependencies
- **Types**: Import from `@/types` using path alias
- **Exports**: Use barrel exports (`index.ts`) for clean imports

## Critical

**Frame Management**
```typescript
// Frame buffer is circular, auto-drops old frames
frameBuffer.push(frame);  // Max 100 frames

// Always clean up Object URLs
URL.revokeObjectURL(oldUrl);
```

**Canvas Lifecycle**
```typescript
// Canvas ref MUST be stable - never conditional render
const canvasRef = useRef<HTMLCanvasElement>(null);
<canvas ref={canvasRef} className={hidden ? 'hidden' : ''} />
```
