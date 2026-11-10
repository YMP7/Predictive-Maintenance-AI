"""Every file the title-justification matrix cites must exist (D7: each cell is backed or marked FUTURE-WORK)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "TITLE_JUSTIFICATION.md"
PAGE = ROOT / "client" / "src" / "pages" / "ops" / "EvidencePage.tsx"
# repository paths: things like server/atlas/explain.py, data/x.json, docs/media/screens/p4-fleet-*.png
PATH = re.compile(r"(?<![\w/])((?:server|scripts|data|docs|tests|client)/[\w./*-]+\.(?:py|json|md|png|mp4|ts|tsx|yml))")


def _cited(text: str):
    return sorted(set(PATH.findall(text)))


def test_every_path_in_the_justification_doc_exists():
    cited = _cited(DOC.read_text(encoding="utf-8"))
    assert len(cited) > 20
    missing = [p for p in cited if not list(ROOT.glob(p))]
    assert missing == []


def test_every_path_on_the_evidence_page_exists():
    cited = _cited(PAGE.read_text(encoding="utf-8"))
    assert len(cited) > 10
    missing = [p for p in cited if not list(ROOT.glob(p))]
    assert missing == []


def test_docker_compose_and_the_film_exist():
    assert (ROOT / "docker-compose.yml").exists()
    assert (ROOT / "docs" / "media" / "films" / "p3-asset-tour.mp4").exists()
