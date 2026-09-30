# Hearth console

The console uses Animal Island UI 2.0.0, React 19, and Naive Icons. Runtime operation
pages consume structured page data; other management workflows render the existing
server-defined forms using the same component controls and permission boundaries.

```sh
cd frontend
npm ci
npm run typecheck
npm run build
```

The build writes self-contained assets into `src/hearth/web/static/island/`. These
assets are included in the Python package. Production requires neither Node nor a
frontend development server. Built assets are committed so the normal Python-only
deployment flow also works.

## Localization

Python templates and React share `src/hearth/web/locales/zh-CN.json` and `en.json`.
Strings are authored and reviewed against the actual behavior, not submitted to a
translation service. See `docs/terminology.zh-CN.md` for the terminology contract.
Dynamic identifiers, user content, and original diagnostic logs are preserved.

`island-localization.ts` supplies authored labels for upstream components that do
not expose a locale prop. A narrowly scoped Vite transform binds the upstream
notification portal to the application's React 19 client entrypoint.

## Assets and typography

The selected scene SVGs are from the official animal-island-ui repository, retrieved
on 2026-09-30. Their MIT license and third-party package notices are bundled under
`/static/island/legal/`. Fonts use the SIL Open Font License.

The shipped Chinese UI subset and local Nunito fonts retain the library typography
without loading several full CJK fonts on every page. The full Noto fallback is used
only for characters outside the UI subset. After changing copy, regenerate with:

```sh
python -m pip install fonttools brotli
python frontend/build_fonts.py
```

The font-generation dependencies are build tools, not production dependencies.
