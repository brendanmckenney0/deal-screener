"""Pipeline: extract -> normalize -> reconcile -> gap report -> memo."""

import os

from . import extract as _extract
from . import guardrails
from . import memo as _memo
from .providers import get_provider


def analyze_pdf(pdf_path, provider_name=None):
    pages = _extract.extract_pages(pdf_path)
    provider = get_provider(provider_name)
    fields = provider.extract_fields(pages)

    issues = guardrails.validate(fields)
    reconciliation = guardrails.reconcile(fields)
    gaps = guardrails.gap_report(fields)

    result = {
        "file": os.path.basename(pdf_path),
        "provider": provider.name,
        "pages": len(pages),
        "fields": fields,
        "validation_issues": issues,
        "reconciliation": reconciliation,
        "gaps": gaps,
    }
    result["memo"] = _memo.build_memo(result)
    return result
