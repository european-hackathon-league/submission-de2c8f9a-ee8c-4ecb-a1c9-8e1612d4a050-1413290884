# Working in BMWow

Read `README.md` for setup and layout, `docs/ontology.md` for ontology meaning,
and `docs/web-research.md` for the proposed collection interface.

## Shared project conventions

- All Python work uses root `pyproject.toml`, `uv.lock`, and uv. Put importable
  Python modules in `backend/bmwow/`; do not add separate leaf projects.
- The frontend uses root `package.json`, `pnpm-lock.yaml`, and `src/app/`.
- Pydantic models in `backend/bmwow/ontology/models.py` and Python relationship
  rules are the ontology source of truth. Generate contracts with
  `uv run bmwow-schema`; do not manually edit generated `schema.json` or `vocabulary.json`.
- `contracts/ontology/source-mappings.json` and the synthetic fixture are maintained
  by hand. Guides belong in `docs/`, and Python tests belong in `tests/`.
- Preserve `bmwow.ontology` imports, wire IDs, field names, and the ontology version
  when making internal refactors. Coordinate breaking contract changes with the team.
- Run `validate_bundle` on complete merged snapshots before accepting agent proposals;
  Pydantic structure checks alone do not validate evidence chains or human review.

## Collaboration and data

- Inspect Git status before editing and preserve other teammates' changes.
- Work on a separate feature branch. Coordinate edits to shared contracts, lockfiles,
  IDs, and API boundaries with the ontology, orchestration, and frontend owners.
- Add dependencies with `uv add` or `pnpm add` and include the corresponding lockfile.
- Keep original BMW data, derived real-data samples, credentials, local databases,
  logs, and local environments out of Git. Shared fixtures must use synthetic content.
- Commit `AGENTS.md`, docs, shared configuration, lockfiles, and generated contracts.
- Before pushing, review the staged diff and the Entire checkpoint-upload behavior
  described in `README.md`; ignored files do not exclude transcripts stored in Git refs.

## Relevant checks

For Python or ontology changes, run `uv run pytest`, `uv run ruff check .`,
`uv run ruff format --check .`, `uv run bmwow-schema --check`, and
`uv run bmwow-validate contracts/ontology/examples/synthetic.json`.
For frontend changes, run the relevant pnpm lint, format, and build checks.
Update the README or guides when setup, paths, contracts, or integration behavior changes.

<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
