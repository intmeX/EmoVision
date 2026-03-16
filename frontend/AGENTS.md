# Frontend Knowledge Base

React 18 + TypeScript + Vite + Tailwind + Zustand emotion recognition UI.

## Structure
```
frontend/
├── src/           # Application code (see src/AGENTS.md)
├── public/        # Static assets
├── index.html     # Entry HTML
├── package.json   # Dependencies + scripts
├── vite.config.ts # Vite bundler config
├── tsconfig.json  # TypeScript strict mode
├── .eslintrc.json # ESLint rules
└── tailwind.config.js
```

## Where to Look

| Task | Location | Notes |
|------|----------|-------|
| Start dev server | `npm run dev` | Port 5173 |
| Add component | `src/components/` | See src/components/AGENTS.md |
| Add hook | `src/hooks/` | Custom React hooks |
| State management | `src/store/` | Zustand stores |
| API calls | `src/services/api.ts` | REST endpoints |
| WebSocket | `src/services/websocket.ts` | Binary protocol |
| Types | `src/types/` | TypeScript definitions |

## Commands

```bash
# Setup
npm install

# Dev server (port 5173)
npm run dev

# Build
npm run build

# Lint (zero warnings required)
npm run lint

# Type check
npx tsc --noEmit
```

## Conventions

- **TypeScript**: Strict mode, `noUnusedLocals`, `noUnusedParameters`
- **Imports**: Use `@/*` path alias for src imports
- **Naming**: `PascalCase` (components/types), `camelCase` (funcs/vars)
- **Components**: Functional only, one per file
- **State**: Zustand stores in `store/` directory
- **ESLint**: `@typescript-eslint/no-explicit-any` is `warn` (avoid `any`)

## Critical Patterns

**Canvas Rendering**
```typescript
// Canvas MUST always be in DOM - use hidden class, NOT conditional render
<canvas className={isRunning ? '' : 'hidden'} />

// Use createImageBitmap for efficient decoding
const bitmap = await createImageBitmap(blob);
ctx.drawImage(bitmap, 0, 0, width, height);
bitmap.close();
URL.revokeObjectURL(url);  // Clean up Object URLs
```

**WebSocket Protocol**
```typescript
// Receive JSON header, then blob
const header = JSON.parse(textMessage);
const blob = await blobMessage;
const imageUrl = URL.createObjectURL(blob);
```

## Anti-Patterns

- Use `any`, `@ts-ignore`, `as any` (violates strict typing)
- Conditionally render Canvas (breaks ref binding)
- Forget to revoke Object URLs (memory leak)
- Skip cleanup in useEffect (resource leaks)

## Notes

- No unit test framework (Vitest/Jest) - relies on TypeScript + ESLint
- Dark theme with Tailwind CSS
- Real-time frame rendering via WebSocket binary protocol
