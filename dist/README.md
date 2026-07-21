# Ready-to-go offline bundles

**All-in-one, fully-offline** builds — everything included (a standalone Python, `uv`, all
dependencies, the model, and the voices). No Python, no internet, no admin rights on the target.

| Bundle | Model | Size | Speed (short sentence) |
|--------|-------|-----:|-----------------------|
| `translator-offline-1.3B.zip` | NLLB-200 1.3B | ~2.0 GB | ~0.2 s |
| `translator-offline-3.3B.zip` | NLLB-200 3.3B | ~3.7 GB | ~0.4 s, best quality |

These are **too large to commit to a GitHub repo** (LFS free tier is 1 GB), so they're published as
**GitHub Release assets** rather than in the tree. Grab one from the repo's **Releases** page,
unzip, and double-click `run-gui.bat` — fully offline from there.

*(The 3.3B zip exceeds GitHub's 2 GB per-file Release limit, so it's split into parts; download
all parts and run the included join step, or use 7-Zip which rejoins automatically.)*

## Prefer a smaller download?

Clone the repo and run `setup.bat 1.3B` (or `600M` / `3.3B`). That installs `uv` + deps and
downloads only the model you pick from HuggingFace — the code checkout itself is under 1 MB.
