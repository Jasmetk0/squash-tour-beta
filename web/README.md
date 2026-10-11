# Squash Tour Beta Engine Web UI (MVP)

Basic React + TypeScript + Vite UI shell for deterministic simulation control and read-only exploration.

## Run locally

```bash
cd web
npm install
npm run dev
```

The UI expects the FastAPI backend at `http://127.0.0.1:8000` by default.
Override with:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

The default season sent by the create-run form is aligned to the current configured backend calendar season (`2027`), and can be overridden with:

```bash
VITE_SUPPORTED_SEASON=2027 npm run dev
```

## Available MVP pages

- Dashboard: health check, create run, load run by run ID.
- Run detail: summary + simulation controls (next tournament/week/full season).
- Events: completed event list + event payload detail.
- Ranking snapshots: list + payload detail.
- Race snapshots: list + payload detail.

## Testing

```bash
npm run test
```
