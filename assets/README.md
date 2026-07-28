# Brand assets

Drop the Finley Golf Club logo here as **`finley-logo.png`** (transparent
background works best). When present, `tools/build_live_tracker_xlsx.py`
embeds it on the Summary tab of the live tracker automatically. Without it,
the builder falls back to a styled "FINLEY · GOLF CLUB" wordmark.

Brand colors used across the tracker:

- Navy (wordmark): `#13294B`
- Pine / pinecone light blue (accent): `#9FC2E6`

After adding or changing the logo, rebuild and re-import the sheet:

```
python3 tools/build_live_tracker_xlsx.py "Sales Tracker (live).xlsx"
```
