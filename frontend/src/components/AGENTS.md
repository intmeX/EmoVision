# Frontend UI Components

React components for the EmoVision interface.

## Core Structure
- **`config/`**: Pipeline configuration panels.
- **`dashboard/`**: Real-time stats and emotion distribution charts.
- **`layout/`**: Application shell components.
- **`results/`**: Results timeline and control section.
- **`video/`**: Video player and source selector.
- **`common/`**: Empty (dead folder).

## Key Components
- **`video/VideoPlayer.tsx`**: Main visual rendering. Integrates with `api.ts`, `frameBuffer.ts`.
- **`results/ResultsControlSection.tsx`**: Results management, export, and timeline interactions.

## Critical Rendering Pattern: The Canvas
1. **Never conditionally render the canvas**. Keep in DOM to maintain ref bindings.
2. Toggle visibility with Tailwind `hidden`: `<canvas className={isRunning ? '' : 'hidden'} />`.
3. Use `createImageBitmap` for high-performance decoding before context drawing.

## State Management
- Prefer Zustand stores (`pipelineStore`, `configStore`) over prop drilling.
