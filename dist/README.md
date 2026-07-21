# Ready-to-go offline bundles

**All-in-one, fully-offline** builds — everything is included (a standalone Python, `uv`, all
dependencies, the model, and the voices). No Python, no internet, no admin rights on the target.

Download them from the repo's **[Releases](../../releases)** page (they're too big to sit in the
git tree). Then unzip and double-click **`run-gui.bat`** inside — offline from there on.

| Bundle | Model | Download | Speed (short sentence) |
|--------|-------|----------|-----------------------|
| `translator-offline-1.3B.zip` | NLLB-200 1.3B | one file (~1.9 GB) | ~0.2 s |
| `translator-offline-3.3B` | NLLB-200 3.3B | 3 parts (~3.6 GB total) + rejoin | ~0.4 s, best quality |

## 1.3B — just download and unzip
`translator-offline-1.3B.zip` is a single file. Download it, unzip, run `run-gui.bat`.

## 3.3B — download the parts, then auto-reassemble
GitHub caps a Release file at 2 GB, so the 3.3B bundle is split. From the Release, download **all**
of these into one folder:

```
translator-offline-3.3B.zip.part00
translator-offline-3.3B.zip.part01
translator-offline-3.3B.zip.part02
reassemble-3.3B.bat
```

Then **double-click `reassemble-3.3B.bat`**. It rejoins the parts into
`translator-offline-3.3B.zip`, verifies the checksum, and tells you when it's done. Unzip that and
run `run-gui.bat`.

**macOS / Linux** (or if you prefer the command line):
```bash
cat translator-offline-3.3B.zip.part* > translator-offline-3.3B.zip
shasum -a 256 translator-offline-3.3B.zip
# expect: 6eb7c9761c2021b025a32aa2ce4a9bf1912ba31118643892c4817a2ee67c7c70
```
7-Zip users can also just open `.part00` and it rejoins automatically.

## Prefer a smaller download?
Clone the repo and run `setup.bat 1.3B` (or `600M` / `3.3B`) — it installs `uv` + deps and
downloads only the model you pick. The code checkout itself is under 1 MB.
