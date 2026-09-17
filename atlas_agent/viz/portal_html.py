"""Portal — redirect to Discovery table (single-purpose site)."""
from __future__ import annotations

from pathlib import Path


def generate_portal_html(
    out_path: str | Path,
    *,
    meta: dict | None = None,
    deploy: str = "docs_portal",
) -> Path:
    del meta, deploy
    target = "site/discovery.html"
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <meta http-equiv="refresh" content="0;url={target}"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Discovery — TMT Atlas</title>
  <script>location.replace("{target}");</script>
</head>
<body><p><a href="{target}">Discovery</a></p></body>
</html>""",
        encoding="utf-8",
    )
    return out
