from __future__ import annotations

import markdown
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render

from . import nav as nav_module
from .nav import NAV


def index(request: HttpRequest) -> HttpResponse:
    return render(request, "docs/index.html", {"nav": NAV})


def page(request: HttpRequest, section: str, slug: str) -> HttpResponse:
    path = nav_module.resolve(section, slug)
    if path is None:
        raise Http404

    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise Http404

    extensions = ["fenced_code", "tables", "toc", "codehilite"]
    extension_configs = {"codehilite": {"guess_lang": False}}
    content = markdown.markdown(text, extensions=extensions, extension_configs=extension_configs)

    current_label = ""
    current_section_label = ""
    for s in NAV:
        if s["slug"] == section:
            section_label = s["section"]
            current_section_label = section_label if isinstance(section_label, str) else ""
            entries = s["entries"]
            if not isinstance(entries, list):
                continue
            for e in entries:
                if not isinstance(e, dict):
                    continue
                if e["slug"] == slug:
                    entry_label = e["label"]
                    current_label = entry_label if isinstance(entry_label, str) else ""

    return render(
        request,
        "docs/page.html",
        {
            "nav": NAV,
            "content": content,
            "current_section": section,
            "current_slug": slug,
            "current_label": current_label,
            "current_section_label": current_section_label,
        },
    )
