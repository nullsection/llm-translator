# Ready-to-go offline bundles

**All-in-one, fully-offline** builds — everything is included (a standalone Python, `uv`, all
dependencies, the model, and the voices). No Python, no internet, no admin rights on the target.

Download them from the repo's **[Releases](../../releases)** page (they're too big to sit in the
git tree). GitHub caps a Release file at 2 GB, so each bundle is split into parts with a small
`reassemble-*.bat` that rejoins and verifies them. Then unzip and double-click **`run-gui.bat`**
inside — offline from there on.

| Bundle | Model | Download | Speed (short sentence) |
|--------|-------|----------|-----------------------|
| `translator-offline-1.3B` | NLLB-200 1.3B | 2 parts (~2.1 GB total) + rejoin | ~0.2 s |
| `translator-offline-3.3B` | NLLB-200 3.3B | 3 parts (~3.8 GB total) + rejoin | ~0.4 s, best quality |

Both bundles include English (male and female), Chinese, and Japanese (male and female) voices,
ready offline; other languages download a voice on first use.

## Download the parts, then auto-reassemble

From the Release, download **all** the parts for your chosen bundle plus its `.bat`, into one
folder. For 1.3B:

```
translator-offline-1.3B.zip.part00
translator-offline-1.3B.zip.part01
reassemble-1.3B.bat
```

For 3.3B:

```
translator-offline-3.3B.zip.part00
translator-offline-3.3B.zip.part01
translator-offline-3.3B.zip.part02
reassemble-3.3B.bat
```

Then **double-click the `reassemble-*.bat`**. It rejoins the parts into the full `.zip`, verifies
the checksum, and tells you when it's done. Unzip that and run `run-gui.bat`.

**macOS / Linux** (or if you prefer the command line):
```bash
# 1.3B
cat translator-offline-1.3B.zip.part* > translator-offline-1.3B.zip
shasum -a 256 translator-offline-1.3B.zip
# expect: 0f26e41bdf3d531cee246cfe188cb097c3456c80dbc51bdf85dc5715ced86b1f

# 3.3B
cat translator-offline-3.3B.zip.part* > translator-offline-3.3B.zip
shasum -a 256 translator-offline-3.3B.zip
# expect: ffa94fd899362bb3251becb73909f966d4222a0fdd737e80c47fb070c1fa719a
```
7-Zip users can also just open `.part00` and it rejoins automatically.

## Prefer a smaller download?
Clone the repo and run `setup.bat 1.3B` (or `600M` / `3.3B`) — it installs `uv` + deps and
downloads only the model you pick. The code checkout itself is under 1 MB.
