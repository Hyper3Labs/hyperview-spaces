# Archived Live Spaces and drafts

Archived on 2026-09-11 at the owner's request. Nothing was permanently deleted.
Hugging Face exposes pause/restart rather than a repository archive control in
the supported API. Existing HF repositories retain their URLs and Git history;
the runtime is paused and the Space card carries a retirement notice.

| Demo | Preserved source | Published replacement |
| --- | --- | --- |
| ABO Catalog live runtime | `../demos/abo-catalog-clip-hycoclip/` | https://spaces.hyper3labs.com/abo-catalog/ |
| Logo Search live runtime | `../demos/logo-brand-search-clip-hyper3clip/` | https://spaces.hyper3labs.com/logo-search/ |
| GeoSpatial live runtime | `../demos/geospatial-eurosat-clip-hyper3clip/` | https://spaces.hyper3labs.com/geospatial/ |
| Visual Safety live runtime | `../demos/visual-safety-content-clip-hyper3clip/` | https://spaces.hyper3labs.com/visual-safety/ |
| VisA Manufacturing | `demos/manufacturing-visa-reference-clip-hyper3clip/` | None; the existing HF Space remains paused |
| Art Text Search draft | `demos/art-text-search-clip-hyper3clip/` | None; no HF repository exists for the registered ID |

The four static demo sources stay in `demos/` because they still produce active
Static Spaces. Precision Regions is also an active Static Space, not an
abandoned draft. Hello World, DeepFashion, and Jaguar remain live.

The ABO and VisA caller workflows are retained under `workflows/`, outside
`.github/workflows/`, and were disabled in GitHub Actions. Archived registry
entries cannot keep warm, declare an HF deployment target, or have an active
caller workflow; `scripts/check_spaces.py` enforces these rules.
The manual publisher also refuses archived targets until their lifecycle is
explicitly restored in the registry.

## Restore a Live Space

1. Change its registry status to `live`, remove `archived_at` and `archive_reason`,
   and restore the required HF deployment target and keep-warm policy.
2. For a wholly retired demo, move its source back to `demos/` and update the
   registry folder and README table. Check old package pins before deploying.
3. Restore its caller workflow from `workflows/` if applicable, then explicitly
   enable it in GitHub Actions. Preserve its filename for HF Trusted Publisher.
4. Remove the Space card's archive notice, publish if needed, and explicitly
   restart the Space. Verify its dataset and health before advertising it.

Jaguar is intentionally excluded from this archive. Its paper-facing URL must
remain intact; see [the static migration notes](../docs/jaguar-static-migration.md).
