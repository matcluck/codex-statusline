#!/usr/bin/env python3
"""Install native Codex TUI presets with validated merges and guarded undo."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parent


def merge(source, settings):
    """Preserve source formatting outside the managed TUI assignments."""
    before = tomllib.loads(source)
    lines = source.splitlines(keepends=True)
    header = re.compile(r'^\s*\[(?:tui|"tui"|\'tui\')\]\s*(?:#.*)?$')
    starts = [i for i, line in enumerate(lines) if header.match(line.strip())]
    if not starts:
        if 'tui' in before:
            raise ValueError('Unsupported TUI layout; use a standalone [tui] table.')
        result = source.rstrip() + '\n\n[tui]\n'
    else:
        start = starts[0] + 1
        end = start
        kept = []
        while end < len(lines):
            line = lines[end]
            if line.lstrip().startswith('['):
                break
            if not line.strip() or line.lstrip().startswith('#'):
                kept.append(line)
                end += 1
                continue
            chunk = line
            end += 1
            while True:
                try:
                    assignment = tomllib.loads(chunk)
                    break
                except tomllib.TOMLDecodeError:
                    if end >= len(lines):
                        raise ValueError('Cannot safely parse TUI assignment.')
                    chunk += lines[end]
                    end += 1
            if not set(assignment).intersection(settings):
                kept.append(chunk)
        result = ''.join(lines[:start] + kept)
        if not result.endswith('\n'):
            result += '\n'
    additions = ''.join(f'{key} = {json.dumps(value)}\n' for key, value in settings.items())
    result += additions
    if starts:
        result += '\n' + ''.join(lines[end:])
    expected = copy.deepcopy(before)
    expected.setdefault('tui', {}).update(settings)
    if tomllib.loads(result) != expected:
        raise ValueError('Merge would change unrelated settings; no files written.')
    return result


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data, mode):
    fd, name = tempfile.mkstemp(prefix='.codex-statusline-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            os.fchmod(output.fileno(), mode)
            output.write(data)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preset', choices=['recommended', 'compact', 'detailed'], default='recommended')
    parser.add_argument('--config', type=Path, default=Path.home() / '.codex/config.toml')
    parser.add_argument('--undo', type=Path, metavar='BACKUP')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    path = args.config.expanduser().resolve()
    existed = path.exists()
    original = path.read_bytes() if existed else b''
    mode = stat.S_IMODE(path.stat().st_mode) if existed else 0o600
    if args.undo:
        backup = args.undo.expanduser().resolve()
        metadata = json.loads(Path(str(backup) + '.json').read_text())
        restored = backup.read_bytes()
        if metadata['config'] != str(path) or digest(original) != metadata['installed_sha256']:
            raise ValueError('Config changed since installation or target differs; undo refused.')
        if digest(restored) != metadata['backup_sha256']:
            raise ValueError('Backup changed; undo refused.')
        tomllib.loads(restored.decode())
        if not args.dry_run:
            if metadata['existed']:
                atomic_write(path, restored, metadata['mode'])
            else:
                path.unlink()
        print('Undo validated.' if args.dry_run else 'Previous config restored.')
        return
    preset = ROOT / ('recommended-config.toml' if args.preset == 'recommended' else f'presets/{args.preset}.toml')
    settings = tomllib.loads(preset.read_text())['tui']
    current = tomllib.loads(original.decode()).get('tui', {})
    if all(current.get(key) == value for key, value in settings.items()):
        print('Selected preset already installed; no changes.')
        return
    updated = merge(original.decode(), settings).encode()
    if args.dry_run:
        print(json.dumps(settings, indent=2))
        print('Merge validated; no files written.')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + '.statusline-', suffix='.bak', dir=path.parent)
    with os.fdopen(fd, 'wb') as backup:
        backup.write(original)
    metadata = {'config': str(path), 'existed': existed, 'mode': mode,
                'installed_sha256': digest(updated), 'backup_sha256': digest(original)}
    atomic_write(Path(name + '.json'), json.dumps(metadata).encode(), 0o600)
    if (path.read_bytes() if path.exists() else b'') != original:
        raise ValueError('Config changed during installation; retry.')
    atomic_write(path, updated, mode)
    print(f'Installed {args.preset} preset in {path}')
    print(f'Backup: {name}')
    undo_command = ['python3', str(ROOT / 'install.py'), '--config', str(path), '--undo', name]
    print(f'Undo: {shlex.join(undo_command)}')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(f'Error: {error}')
