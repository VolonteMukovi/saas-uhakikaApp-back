"""Règle 4 — Accept-Ranges / Range / 206 Partial Content."""
from __future__ import annotations

import re

from django.http import FileResponse, HttpResponse

_RANGE_RE = re.compile(r'bytes=(\d*)-(\d*)')


def ranged_bytes_response(request, data: bytes, content_type: str, *, filename: str | None = None) -> HttpResponse:
    """
    Réponse binaire avec support Range (206) pour PDF, CSV, exports.
    """
    size = len(data)
    response = HttpResponse(content_type=content_type)
    response['Accept-Ranges'] = 'bytes'
    if filename:
        response['Content-Disposition'] = f'inline; filename="{filename}"'

    range_header = request.META.get('HTTP_RANGE', '').strip()
    if not range_header or size == 0:
        response.status_code = 200
        response.write(data)
        return response

    m = _RANGE_RE.match(range_header)
    if not m:
        response.status_code = 200
        response.write(data)
        return response

    start_s, end_s = m.groups()
    start = int(start_s) if start_s else 0
    end = int(end_s) if end_s else size - 1
    if start >= size or start > end:
        response.status_code = 416
        response['Content-Range'] = f'bytes */{size}'
        return response

    end = min(end, size - 1)
    chunk = data[start:end + 1]
    response.status_code = 206
    response['Content-Range'] = f'bytes {start}-{end}/{size}'
    response['Content-Length'] = str(len(chunk))
    response.write(chunk)
    return response


def file_stream_response(path, content_type: str, *, filename: str | None = None) -> FileResponse:
    """Flux fichier disque avec Accept-Ranges (Django FileResponse)."""
    response = FileResponse(open(path, 'rb'), content_type=content_type, as_attachment=False)
    response['Accept-Ranges'] = 'bytes'
    if filename:
        response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response
