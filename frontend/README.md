# SHIFT//OS frontend prototype

Clickable prototype of the Phase 8 demo UI (`prompts/08_MINIMAL_DEMO_UI.md`). It runs entirely on the synthetic fixtures in `../fixtures/` and calls no backend yet.

```bash
npm install
npm run dev     # http://localhost:5173
npm run check   # analysis rule self-check
npm run build
```

Flow: programme explorer → run whole-programme analysis → course evidence inspector with options compared (incl. no change) → snapshot/scenario toggle (shows "Changed vs syn-snap-A") → draft report.

`src/analysis.ts` is a stand-in for the future `/api/v1/programmes/{id}/analyses` endpoints. Swap it for `fetch` calls once the backend analysis exists. All data shown is fictional and labelled synthetic.
