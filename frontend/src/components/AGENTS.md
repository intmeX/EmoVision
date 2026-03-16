# UI Components

React functional components organized by feature.

## Structure
```
components/
├── common/        # Shared/reusable components (empty currently)
├── config/        # Configuration panels
├── dashboard/     # Stats and charts
├── layout/        # App layout (Header, Sidebar, MainLayout)
├── results/       # Results display and timeline
└── video/         # Video player and source selector
```

## Where to Look

| Task | Location |
|------|----------|
| Modify config UI | `config/ConfigPanel.tsx` |
| Change detector settings | `config/DetectorConfig.tsx` |
| Change recognizer settings | `config/RecognizerConfig.tsx` |
| Modify visualization | `config/VisualizerConfig.tsx` |
| Update stats display | `dashboard/StatsPanel.tsx` |
| Modify emotion chart | `dashboard/EmotionChart.tsx` |
| Change layout | `layout/MainLayout.tsx` |
| Video player | `video/VideoPlayer.tsx` |
| Source selection | `video/SourceSelector.tsx` |

## Component Pattern

```typescript
// Functional component with TypeScript
interface Props {
  value: string;
  onChange: (value: string) => void;
}

export function MyComponent({ value, onChange }: Props) {
  // Use hooks for state/effects
  // Return JSX
}
```

## Conventions

- **One component per file**, named same as file
- **Props interface** defined above component
- **Barrel exports** via `index.ts` for clean imports
- **Tailwind CSS** for styling (dark theme)
- **Lucide React** for icons

## Component Groups

**config/**: Collapsible panels for pipeline configuration
**dashboard/**: Real-time stats (FPS, latency) and emotion distribution charts
**layout/**: App shell (header, sidebar, main content area)
**results/**: Results timeline and export controls
**video/**: Video display canvas and source upload/selection

## Notes

- `common/` directory exists but is empty (reserved for shared components)
- All components use Zustand stores for state (no prop drilling)
- Canvas rendering happens in `video/VideoPlayer.tsx`
