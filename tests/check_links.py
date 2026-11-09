#!/usr/bin/env python3
"""Check local Markdown link files and heading fragments without network access."""
from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
errors = []
for source in ROOT.rglob('*.md'):
    if '.git' in source.parts:
        continue
    text = source.read_text()
    for target in re.findall(r'(?<!!)\[[^\]]*\]\(([^\s)]+)(?:\s+"[^\"]*")?\)', text):
        if re.match(r'[a-z]+:', target) or target.startswith('//'):
            continue
        filename, _, fragment = unquote(target).partition('#')
        path = (source.parent / filename).resolve() if filename else source
        if not path.exists():
            errors.append(f'{source.relative_to(ROOT)}: missing {target}')
        elif fragment and path.is_file() and path.suffix == '.md':
            headings = []
            counts = {}
            fenced = False
            for line in path.read_text().splitlines():
                if line.startswith('```'):
                    fenced = not fenced
                if fenced or not re.match(r'^#{1,6} ', line):
                    continue
                heading = re.sub(r'^#{1,6} ', '', line).strip().lower()
                slug = re.sub(r'[^\w\- ]', '', heading).replace(' ', '-')
                n = counts.get(slug, 0)
                headings.append(slug + (f'-{n}' if n else ''))
                counts[slug] = n + 1
            if fragment not in headings:
                errors.append(f'{source.relative_to(ROOT)}: missing heading {target}')
if errors:
    print('\n'.join(errors))
    sys.exit(1)
print('Local Markdown files and heading links passed.')
