# Delete Manifest: Retire REQ-018 Decomposition File

## File to delete

- `stream_lite/docs/reqs/REQ-018-contract-decomposition-and-implementation-readiness.md`

## Reason

The project requirement workflow keeps decomposition inside the owning capability requirement files. A standalone decomposition requirement file creates ambiguity about ownership and conflicts with the L1/L2/L3 model introduced in `REQ-000`.

## Disposition

The former `SL-DECOMP-*` requirements are retained and migrated into `stream_lite/docs/reqs/REQ-000-requirements-quality-and-ambiguity-control.md` under `Contract Artifact Readiness Requirements`.

## Verification

After migration, static reference inventory shall show zero unresolved requirement references and no duplicate active requirement rows.
