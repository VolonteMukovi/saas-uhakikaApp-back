"""Normalisation des logos entreprise (formats variés → JPEG/PNG acceptés par ImageField)."""
from __future__ import annotations

import io
from typing import BinaryIO

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.translation import gettext_lazy as _
from PIL import Image, UnidentifiedImageError

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    pass

MAX_EDGE = 2048
MAX_BYTES = 8 * 1024 * 1024


def _open_image(source: BinaryIO) -> Image.Image:
    img = Image.open(source)
    img.load()
    return img


def normalize_entreprise_logo(upload) -> InMemoryUploadedFile:
    """
    Ouvre le fichier avec Pillow, corrige l’orientation EXIF si possible,
    convertit en RGB JPEG (ou PNG si transparence nécessaire).
    """
    if upload is None:
        return upload

    raw = upload.read()
    if not raw:
        raise ValueError(_('Le fichier logo est vide.'))
    if len(raw) > MAX_BYTES:
        raise ValueError(_('Logo trop volumineux (max 8 Mo).'))

    try:
        img = _open_image(io.BytesIO(raw))
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError(
            _('Format d’image non reconnu. Utilisez une photo ou un logo (JPG, PNG, WebP, GIF, BMP, HEIC…).')
        ) from exc

    try:
        from PIL import ImageOps

        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    has_alpha = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
    w, h = img.size
    if w <= 0 or h <= 0:
        raise ValueError(_('Dimensions d’image invalides.'))

    scale = min(1.0, MAX_EDGE / float(max(w, h)))
    if scale < 1.0:
        new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    base_name = (getattr(upload, 'name', None) or 'logo').rsplit('.', 1)[0][:80]

    if has_alpha:
        img = img.convert('RGBA')
        img.save(buf, format='PNG', optimize=True)
        content_type = 'image/png'
        file_name = f'{base_name}.png'
    else:
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(buf, format='JPEG', quality=88, optimize=True)
        content_type = 'image/jpeg'
        file_name = f'{base_name}.jpg'

    buf.seek(0)
    return InMemoryUploadedFile(
        file=buf,
        field_name='logo',
        name=file_name,
        content_type=content_type,
        size=buf.getbuffer().nbytes,
        charset=None,
    )
