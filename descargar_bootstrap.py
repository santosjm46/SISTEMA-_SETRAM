"""Descarga Bootstrap versionado para servirlo localmente."""
from pathlib import Path
from urllib.request import urlopen

root=Path(__file__).resolve().parent / 'static' / 'vendor'
root.mkdir(parents=True,exist_ok=True)
for asset in ('css/bootstrap.min.css','js/bootstrap.bundle.min.js'):
    target=root / asset.split('/')[-1]
    if not target.exists():
        with urlopen('https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/'+asset,timeout=30) as response:
            target.write_bytes(response.read())
    print('Bootstrap local: '+target.name)
