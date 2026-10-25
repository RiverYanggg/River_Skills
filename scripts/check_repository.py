#!/usr/bin/env python3
"""Check skill names, root README catalog and repository-local Markdown links."""
import re
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit


def check(root):
    errors = []
    readme = root / 'README.md'
    if not readme.is_file():
        return ['Missing root README.md'], []
    catalog = set(re.findall(r'\]\(skills/([^/]+)/SKILL\.md\)', readme.read_text()))
    skills = sorted((root / 'skills').glob('*/SKILL.md'))
    names = []
    for entry in skills:
        name = entry.parent.name
        names.append(name)
        text = entry.read_text()
        match = re.match(r'\A---\s*\n(.*?)\n---(?:\n|$)', text, flags=re.S)
        if not match:
            errors.append(str(entry.relative_to(root)) + ': missing YAML frontmatter')
            continue
        fields = match.group(1)
        declared = re.search(r'^name:\s*[\'\"]?([a-z0-9-]+)[\'\"]?\s*$', fields, flags=re.M)
        if not declared or declared.group(1) != name or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name) or len(name) >= 64:
            errors.append(name + ': directory and frontmatter name must match a skill slug under 64 characters')
        if not re.search(r'^description:\s*\S', fields, flags=re.M):
            errors.append(name + ': description is missing')
        if '[TODO:' in text:
            errors.append(name + ': unfinished scaffold')
        if name not in catalog:
            errors.append(name + ': missing from README skill catalog')
    for stale in sorted(catalog - set(names)):
        errors.append('README references a missing skill: ' + stale)
    for path in sorted(root.rglob('*.md')):
        if any(part in ('.git', '__pycache__', '.venv') for part in path.relative_to(root).parts):
            continue
        text = path.read_text()
        for match in re.finditer(r'\]\(([^)\n]+)\)', text):
            destination = match.group(1).strip()
            if destination.startswith('<') and destination.endswith('>'):
                destination = destination[1:-1]
            parsed = urlsplit(destination)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            if parsed.path.startswith('/'):
                errors.append(str(path.relative_to(root)) + ': absolute local link is not portable: ' + destination)
                continue
            target = (path.parent / unquote(parsed.path)).resolve()
            try:
                target.relative_to(root)
            except ValueError:
                errors.append(str(path.relative_to(root)) + ': local link leaves the repository: ' + destination)
                continue
            if not target.exists():
                errors.append(str(path.relative_to(root)) + ': broken local link: ' + destination)
    return errors, names


if __name__ == '__main__':
    repository = Path(__file__).resolve().parents[1]
    problems, names = check(repository)
    if problems:
        print('\n'.join('ERROR: ' + problem for problem in problems), file=sys.stderr)
        sys.exit(1)
    print('PASS: skill catalog, names and local Markdown links (' + ', '.join(names) + ')')
