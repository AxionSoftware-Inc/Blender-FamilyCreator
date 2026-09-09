# Blender 5.2 runtime harness

This harness runs the addon inside the installed Blender runtime. It creates
deterministic synthetic assets, exercises the exact-class generators, exports
and re-imports GLB packages, renders thumbnails, tests variants and batch
conversion, and writes a machine-readable result file under `artifacts/`.

Run it from the repository root with the detected Blender executable:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --python tests/blender_runtime/run_all.py
```

The script intentionally does not use normal system Python for Blender-facing
checks. Pure-Python regression tests remain:

```powershell
python -m unittest discover -s tests -v
```

