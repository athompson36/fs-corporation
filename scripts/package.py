"""Create a clean starter archive with per-file SHA-256 manifest.

Run from the project root: python3 scripts/package.py
Build output: dist/fs-tech-ai-company-cursor-starter.zip
"""
import hashlib
from pathlib import Path
import zipfile

root=Path(__file__).resolve().parents[1]
ignored={'.git','.venv','.local','__pycache__','dist','build','upstream','workspaces','artifacts'}
def eligible(p):
    rel=p.relative_to(root)
    if any(part in ignored or part.endswith('.egg-info') for part in rel.parts):return False
    if p.name.startswith('.env') and p.name!='.env.example':return False
    return p.suffix not in {'.pyc','.db','.zip'} and p.name!='CHECKSUMS.sha256'

files=sorted(p for p in root.rglob('*') if p.is_file() and eligible(p))
manifest=root/'CHECKSUMS.sha256'
manifest.write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root).as_posix()}\n' for p in files))
files.append(manifest)
out=root/'dist'/'fs-tech-ai-company-cursor-starter.zip'
out.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for p in files:
        info=zipfile.ZipInfo('fs-tech-ai-company/'+p.relative_to(root).as_posix(),date_time=(2026,9,1,0,0,0))
        info.compress_type=zipfile.ZIP_DEFLATED
        info.external_attr=0o644<<16
        z.writestr(info,p.read_bytes())
print(out)
print(f'{len(files)} files; {out.stat().st_size} bytes')
