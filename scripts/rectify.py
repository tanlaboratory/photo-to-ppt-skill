#!/usr/bin/env python3
"""Evidence-preserving geometry helper. Requires Pillow and NumPy.
No boundary detection, OCR rewriting, or generative filling is performed.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def fresh(path):
    if path.exists():
        raise ValueError(f'Refusing to overwrite: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)


def natural(path):
    return [int(s) if s.isdigit() else s.lower()
            for s in re.split(r'(\d+)', str(path))]


def inventory(folder, output):
    if not folder.is_dir():
        raise ValueError('Input must be a directory')
    fresh(output)
    rows = []
    errors = []
    extensions = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.webp', '.heic', '.heif'}
    for p in sorted(folder.rglob('*'), key=natural):
        if not p.is_file() or p.suffix.lower() not in extensions:
            continue
        row = {'source': str(p.relative_to(folder)), 'sha256': digest(p)}
        try:
            with Image.open(p) as raw:
                im = ImageOps.exif_transpose(raw)
                row['oriented_size'] = list(im.size)
        except Exception as e:
            row['read_error'] = str(e)
            errors.append(row['source'])
        rows.append(row)
    # Numeric ordering is only a review order; never claim it is lecture order.
    output.write_text(json.dumps({'source_root': str(folder.resolve()),
                                 'ordering': 'natural filename, requires review',
                                 'photos': rows, 'unreadable': errors},
                                ensure_ascii=False, indent=2))
    print(f'{len(rows)} photos inventoried; {len(errors)} unreadable; none deduplicated')
    if errors:
        raise SystemExit(2)


def homography(src, dst):
    a, b = [], []
    for (x, y), (u, v) in zip(src, dst):
        a.extend([[x, y, 1, 0, 0, 0, -u*x, -u*y],
                  [0, 0, 0, x, y, 1, -v*x, -v*y]])
        b.extend([u, v])
    return np.append(np.linalg.solve(a, b), 1).reshape(3, 3)


def transform(points, h):
    p = np.column_stack([points, np.ones(len(points))]) @ h.T
    if np.any(np.abs(p[:, 2]) < 1e-8):
        raise ValueError('Projective horizon intersects a corner')
    return p[:, :2] / p[:, 2:3], p[:, 2]


def rectify(source, config, output):
    sidecar = Path(str(output) + '.json')
    if output.suffix.lower() != '.png':
        raise ValueError('Intermediate output must be PNG')
    if source.resolve() == output.resolve():
        raise ValueError('Source must remain unchanged')
    fresh(output)
    fresh(sidecar)
    cfg = json.loads(config.read_text())
    with Image.open(source) as raw:
        im = ImageOps.exif_transpose(raw).convert('RGB')
    q = np.asarray(cfg['quad'], dtype=float)
    if q.shape != (4, 2) or not np.isfinite(q).all():
        raise ValueError('quad must contain four finite 2D points')
    scale = np.asarray(cfg.get('coordinate_size', im.size), dtype=float)
    if scale.shape != (2,) or (scale <= 0).any():
        raise ValueError('coordinate_size must have two positive dimensions')
    q *= np.asarray(im.size) / scale
    edges = np.roll(q, -1, axis=0) - q
    cross = edges[:, 0] * np.roll(edges[:, 1], -1) - edges[:, 1] * np.roll(edges[:, 0], -1)
    if not np.all(cross > 1e-6):
        raise ValueError('Expected convex TL, TR, BR, BL quad in image coordinates')
    target = np.asarray(cfg['target_size'], dtype=float)
    if target.shape != (2,) or not np.isfinite(target).all() or (target < 2).any() or (target != target.astype(int)).any():
        raise ValueError('target_size must contain integer dimensions >= 2')
    w, h = target.astype(int)
    dst = np.array([[0, 0], [w-1, 0], [w-1, h-1], [0, h-1]], float)
    matrix = homography(q, dst)
    corners = np.array([[0, 0], [im.width-1, 0],
                        [im.width-1, im.height-1], [0, im.height-1]], float)
    mode = cfg.get('mode', 'crop')
    if mode == 'full-frame':
        bounds, denominators = transform(corners, matrix)
        if not (np.all(denominators > 0) or np.all(denominators < 0)):
            raise ValueError('Horizon crosses photograph; cannot preserve full frame')
        lo, hi = np.floor(bounds.min(axis=0)), np.ceil(bounds.max(axis=0))
        w, h = (hi - lo + 1).astype(int)
        shift = np.array([[1, 0, -lo[0]], [0, 1, -lo[1]], [0, 0, 1]])
        matrix = shift @ matrix
    elif mode != 'crop':
        raise ValueError('mode must be crop or full-frame')
    if w * h > 80_000_000 or min(w, h) < 2:
        raise ValueError('Unreasonable canvas; review geometry and resolution')
    inv = np.linalg.inv(matrix)
    inv /= inv[2, 2]
    out = im.transform((int(w), int(h)), Image.Transform.PERSPECTIVE,
                       inv.flatten()[:8], Image.Resampling.BICUBIC,
                       fillcolor=(255, 255, 255))
    enh = cfg.get('enhance', {})
    gain = np.asarray(enh.get('gain_rgb', [1, 1, 1]), float)
    if gain.shape != (3,) or not np.isfinite(gain).all() or (gain <= 0).any() or (gain > 2).any():
        raise ValueError('gain_rgb must contain 3 positive gains <= 2')
    if not np.all(gain == 1):
        pixels = np.asarray(out, dtype=float) * gain
        out = Image.fromarray(np.clip(pixels, 0, 255).astype('uint8'))
    percent = int(enh.get('unsharp_percent', 0))
    if not 0 <= percent <= 100:
        raise ValueError('unsharp_percent must be 0..100; inspect fine text afterward')
    if percent:
        out = out.filter(ImageFilter.UnsharpMask(radius=.75, percent=percent, threshold=4))
    mapped, _ = transform(corners, matrix)
    out.save(output)
    sidecar.write_text(json.dumps({'source': str(source.resolve()),
        'source_sha256': digest(source), 'oriented_size': list(im.size),
        'config': cfg, 'quad_source_pixels': q.tolist(),
        'source_to_output': matrix.tolist(), 'output_size': [int(w), int(h)],
        'original_corners_in_output': mapped.tolist(),
        'occlusion_repair': 'none', 'outside_source': 'white; no content inferred'},
        ensure_ascii=False, indent=2))
    print(f'{output}: {w}x{h}; {mode}; source unchanged')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    inv = sub.add_parser('inventory')
    inv.add_argument('folder', type=Path)
    inv.add_argument('--output', type=Path, required=True)
    rec = sub.add_parser('rectify')
    rec.add_argument('source', type=Path)
    rec.add_argument('--config', type=Path, required=True)
    rec.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'inventory':
        inventory(args.folder, args.output)
    else:
        rectify(args.source, args.config, args.output)


if __name__ == '__main__':
    main()
