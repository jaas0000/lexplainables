"""Genereer feature-docs uit de code (werkwijze feature-docs skill regel 2).

Deterministisch: dezelfde invoer geeft altijd dezelfde uitvoer. `check` faalt op elke drift
tussen `app/features/<naam>/` en `docs/features/<naam>.md` — dat is been 1 van het
verificatie-principe (`werkwijze/CLAUDE.md` §Verificatie-principe).

Gebruik vanaf de repo-root:
  python scripts/docs/genereer-feature-docs.py generate            # alle features
  python scripts/docs/genereer-feature-docs.py generate feedback   # één feature
  python scripts/docs/genereer-feature-docs.py check               # CI: diff, exit 1 op drift

Deze tool leeft onder `scripts/docs/`, niet in een service — het is projectinfrastructuur die
de code in een service leest en schrijft naar `docs/project/features/`. Alleen stdlib, dus geen
`uv run` nodig.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
FEATURES_DIR = ROOT / "api" / "app" / "features"
DOCS_DIR = ROOT / "docs" / "project" / "features"

VERPLICHTE_SECTIES_SINGLE = ["Wat", "Waarom", "Grens"]
VERPLICHTE_SECTIES_LIST = ["Tabellen", "Beslissingen", "Interacties"]
ALLE_SECTIES = VERPLICHTE_SECTIES_SINGLE + VERPLICHTE_SECTIES_LIST


class DocstringError(ValueError):
    """De module-docstring van een feature voldoet niet aan de conventie."""


# --- Datamodel -----------------------------------------------------------------


@dataclass
class Docstring:
    titel: str
    wat: str
    waarom: str
    grens: str
    tabellen: list[tuple[str, str]]
    beslissingen: list[str]
    interacties: list[str]


@dataclass
class Kolom:
    naam: str
    type_: str
    eigenschappen: list[str]


@dataclass
class Tabel:
    naam: str
    kolommen: list[Kolom]


@dataclass
class Endpoint:
    methode: str
    pad: str
    response_model: str | None
    auth: str | None


@dataclass
class StoreMethode:
    naam: str
    signatuur: str


@dataclass
class StoreProtocol:
    naam: str
    methoden: list[StoreMethode]


@dataclass
class Feature:
    naam: str
    docstring: Docstring
    tabellen: list[Tabel]
    endpoints: list[Endpoint]
    store: StoreProtocol | None
    testnamen: list[str]


# --- Parsen van de docstring ----------------------------------------------------


def parse_docstring(text: str, feature_naam: str) -> Docstring:
    lines = text.strip().splitlines()
    if not lines:
        raise DocstringError(f"{feature_naam}: lege module-docstring.")
    titel = lines[0].rstrip(".").strip()

    single: dict[str, list[str]] = {n: [] for n in VERPLICHTE_SECTIES_SINGLE}
    lists: dict[str, list[str]] = {n: [] for n in VERPLICHTE_SECTIES_LIST}
    huidig_single: str | None = None
    huidig_list: str | None = None

    for raw in lines[1:]:
        line = raw.rstrip()
        stripped = line.strip()

        m = re.match(r"^(\w+):\s*(.*)$", stripped)
        if m and m.group(1) in ALLE_SECTIES:
            naam = m.group(1)
            rest = m.group(2).strip()
            if naam in VERPLICHTE_SECTIES_SINGLE:
                huidig_single = naam
                huidig_list = None
                if rest:
                    single[naam].append(rest)
            else:
                huidig_list = naam
                huidig_single = None
            continue

        if not stripped:
            huidig_single = None
            continue

        if huidig_single and not stripped.startswith("- "):
            single[huidig_single].append(stripped)
            continue

        if huidig_list:
            if stripped.startswith("- "):
                lists[huidig_list].append(stripped[2:].strip())
                continue
            # Vervolgregel op vorige bullet (voor lange list-items die op meerdere
            # regels staan zodat ze onder de 100-char regel-lengte blijven).
            if lists[huidig_list]:
                lists[huidig_list][-1] = f"{lists[huidig_list][-1]} {stripped}"
                continue

    ontbrekend = [
        n for n in VERPLICHTE_SECTIES_SINGLE if not single[n]
    ] + [
        n for n in VERPLICHTE_SECTIES_LIST if not lists[n]
    ]
    if ontbrekend:
        raise DocstringError(
            f"{feature_naam}: ontbrekende sectie(s) in module-docstring: {', '.join(ontbrekend)}"
        )

    def split_tabel(item: str) -> tuple[str, str]:
        if ":" in item:
            naam, rest = item.split(":", 1)
            return naam.strip(), rest.strip()
        return item, ""

    return Docstring(
        titel=titel,
        wat=" ".join(single["Wat"]),
        waarom=" ".join(single["Waarom"]),
        grens=" ".join(single["Grens"]),
        tabellen=[split_tabel(i) for i in lists["Tabellen"]],
        beslissingen=lists["Beslissingen"],
        interacties=lists["Interacties"],
    )


# --- AST-hulpen -----------------------------------------------------------------


def _naam_van(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_naam_van(node.value)}.{node.attr}"
    if isinstance(node, ast.Constant):
        return repr(node.value)
    if isinstance(node, ast.Subscript):
        return f"{_naam_van(node.value)}[{_naam_van(node.slice)}]"
    if isinstance(node, ast.Tuple):
        return ", ".join(_naam_van(e) for e in node.elts)
    if isinstance(node, ast.Call):
        args = [_naam_van(a) for a in node.args]
        args += [f"{kw.arg}={_naam_van(kw.value)}" for kw in node.keywords if kw.arg]
        return f"{_naam_van(node.func)}({', '.join(args)})"
    if isinstance(node, ast.BinOp):
        return f"{_naam_van(node.left)} | {_naam_van(node.right)}"
    return ast.unparse(node)


# --- models.py: tabellen --------------------------------------------------------


def parse_tabellen(pad: Path) -> list[Tabel]:
    if not pad.exists():
        return []
    tree = ast.parse(pad.read_text())
    tabellen: list[Tabel] = []

    # Index-lookup per tabel: verzamel Index(...) calls op module-niveau
    index_kolommen: dict[str, set[str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        call = node.value
        if not isinstance(call.func, ast.Name) or call.func.id != "Table":
            continue
        # args[0] is tabelnaam
        if not (call.args and isinstance(call.args[0], ast.Constant)):
            continue
        tabelnaam = call.args[0].value

        # Verzamel Column-calls en Index-calls binnen deze Table(...)
        kolommen: list[Kolom] = []
        deze_index: set[str] = set()
        for arg in call.args[1:]:
            if not isinstance(arg, ast.Call):
                continue
            inner_naam = _naam_van(arg.func)
            if inner_naam == "Column":
                kolommen.append(_parse_kolom(arg))
            elif inner_naam == "Index":
                # Index(naam, kolom1, kolom2, ...) — voeg alle kolomnamen toe
                for kolom_arg in arg.args[1:]:
                    if isinstance(kolom_arg, ast.Constant):
                        deze_index.add(kolom_arg.value)
        index_kolommen[tabelnaam] = deze_index

        # Markeer kolommen met een index
        for kol in kolommen:
            if kol.naam in deze_index:
                kol.eigenschappen.append("index")

        tabellen.append(Tabel(naam=tabelnaam, kolommen=kolommen))

    return tabellen


def _parse_kolom(call: ast.Call) -> Kolom:
    naam = call.args[0].value if call.args and isinstance(call.args[0], ast.Constant) else "?"
    type_str = _naam_van(call.args[1]) if len(call.args) > 1 else "?"
    eigenschappen: list[str] = []
    nullable_true = False
    for kw in call.keywords:
        if kw.arg == "primary_key" and _bool_van(kw.value) is True:
            eigenschappen.append("primary key")
        elif kw.arg == "autoincrement" and _bool_van(kw.value) is True:
            eigenschappen.append("autoincrement")
        elif kw.arg == "nullable":
            val = _bool_van(kw.value)
            if val is False:
                eigenschappen.append("NOT NULL")
            elif val is True:
                nullable_true = True
        elif kw.arg == "unique" and _bool_van(kw.value) is True:
            eigenschappen.append("unique")
        elif kw.arg == "index" and _bool_van(kw.value) is True:
            eigenschappen.append("index")
        elif kw.arg == "default":
            eigenschappen.append(f"default {_naam_van(kw.value)}")
    if nullable_true and "primary key" not in eigenschappen:
        eigenschappen.append("nullable")
    return Kolom(naam=naam, type_=type_str, eigenschappen=eigenschappen)


def _bool_van(node: ast.AST) -> bool | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return node.value
    return None


# --- router.py: endpoints -------------------------------------------------------


def parse_endpoints(pad: Path) -> list[Endpoint]:
    if not pad.exists():
        return []
    tree = ast.parse(pad.read_text())

    # Router-prefixen ophalen: X = APIRouter(prefix="...")
    prefixen: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "APIRouter":
                for kw in call.keywords:
                    if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                        for tgt in node.targets:
                            if isinstance(tgt, ast.Name):
                                prefixen[tgt.id] = kw.value.value

    endpoints: list[Endpoint] = []
    verben = {"get", "post", "put", "delete", "patch", "head"}

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for deco in node.decorator_list:
            if not isinstance(deco, ast.Call):
                continue
            if not isinstance(deco.func, ast.Attribute):
                continue
            if not isinstance(deco.func.value, ast.Name):
                continue
            verb = deco.func.attr
            if verb not in verben:
                continue
            router_naam = deco.func.value.id
            prefix = prefixen.get(router_naam, "")
            sub = deco.args[0].value if deco.args and isinstance(deco.args[0], ast.Constant) else ""
            pad_volledig = (prefix + sub) or "/"

            response_model: str | None = None
            for kw in deco.keywords:
                if kw.arg == "response_model":
                    response_model = _naam_van(kw.value)

            auth = _auth_van_signatuur(node)

            endpoints.append(
                Endpoint(
                    methode=verb.upper(),
                    pad=pad_volledig,
                    response_model=response_model,
                    auth=auth,
                )
            )

    return endpoints


def _auth_van_signatuur(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    """Zoek in de defaults naar Depends(huidige_<x>) en geef 'x' terug."""
    for default in fn.args.defaults + [k for k in fn.args.kw_defaults if k]:
        if isinstance(default, ast.Call) and _naam_van(default.func) == "Depends":
            if default.args and isinstance(default.args[0], ast.Name):
                dep_naam = default.args[0].id
                if dep_naam.startswith("huidige_"):
                    return dep_naam[len("huidige_"):]
    return None


# --- store.py: Protocol ---------------------------------------------------------


def parse_store(pad: Path) -> StoreProtocol | None:
    if not pad.exists():
        return None
    tree = ast.parse(pad.read_text())
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(isinstance(b, ast.Name) and b.id == "Protocol" for b in node.bases):
            continue
        methoden: list[StoreMethode] = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methoden.append(
                    StoreMethode(naam=item.name, signatuur=_render_signatuur(item))
                )
        return StoreProtocol(naam=node.name, methoden=methoden)
    return None


def _render_signatuur(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args: list[str] = []
    for a in fn.args.args:
        if a.arg == "self":
            continue
        args.append(a.arg)
    ret = _naam_van(fn.returns) if fn.returns else "None"
    prefix = "async " if isinstance(fn, ast.AsyncFunctionDef) else ""
    return f"{prefix}def {fn.name}({', '.join(args)}) -> {ret}: ..."


# --- tests/: getest gedrag ------------------------------------------------------


def parse_testnamen(pad: Path) -> list[str]:
    if not pad.exists() or not pad.is_dir():
        return []
    namen: list[str] = []
    for testbestand in sorted(pad.glob("test_*.py")):
        tree = ast.parse(testbestand.read_text())
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("test_"):
                    namen.append(node.name)
    return namen


def testnaam_naar_zin(naam: str) -> str:
    zonder_prefix = naam[len("test_"):]
    zin = zonder_prefix.replace("_", " ")
    return zin[0].upper() + zin[1:] + "." if zin else ""


# --- Feature verzamelen ---------------------------------------------------------


def parse_feature(feature_dir: Path) -> Feature:
    naam = feature_dir.name
    init_pad = feature_dir / "__init__.py"
    if not init_pad.exists():
        raise DocstringError(f"{naam}: geen __init__.py gevonden.")
    tree = ast.parse(init_pad.read_text())
    doc = ast.get_docstring(tree)
    if not doc:
        raise DocstringError(f"{naam}: geen module-docstring in __init__.py.")

    return Feature(
        naam=naam,
        docstring=parse_docstring(doc, naam),
        tabellen=parse_tabellen(feature_dir / "models.py"),
        endpoints=parse_endpoints(feature_dir / "router.py"),
        store=parse_store(feature_dir / "store.py"),
        testnamen=parse_testnamen(feature_dir / "tests"),
    )


# --- Renderen -------------------------------------------------------------------


def render(feature: Feature) -> str:
    d = feature.docstring
    stukken: list[str] = []

    stukken.append(f"# {d.titel}\n")
    stukken.append(f"{d.wat}\n")
    stukken.append(f"**Waarom apart:** {d.waarom}\n")
    stukken.append(f"**Grens:** {d.grens}\n")

    if feature.tabellen:
        stukken.append("## Datamodel\n")
        tabel_beschrijving = dict(d.tabellen)
        for tabel in feature.tabellen:
            stukken.append(f"### `{tabel.naam}`")
            rol = tabel_beschrijving.get(tabel.naam, "")
            if rol:
                stukken.append(f"{rol}\n")
            stukken.append("| kolom | type | eigenschappen |")
            stukken.append("|---|---|---|")
            for kol in tabel.kolommen:
                eig = ", ".join(kol.eigenschappen) or "—"
                stukken.append(f"| `{kol.naam}` | `{kol.type_}` | {eig} |")
            stukken.append("")

    if feature.endpoints:
        stukken.append("## API\n")
        stukken.append("| Methode | Pad | Auth | Response |")
        stukken.append("|---|---|---|---|")
        for ep in feature.endpoints:
            auth = ep.auth or "—"
            resp = f"`{ep.response_model}`" if ep.response_model else "—"
            stukken.append(f"| `{ep.methode}` | `{ep.pad}` | {auth} | {resp} |")
        stukken.append("")

    if feature.store:
        stukken.append("## Store-interface\n")
        stukken.append("```python")
        stukken.append(f"class {feature.store.naam}(Protocol):")
        for m in feature.store.methoden:
            stukken.append(f"    {m.signatuur}")
        stukken.append("```\n")

    if d.interacties:
        stukken.append("## Interacties\n")
        for i in d.interacties:
            stukken.append(f"- {i}")
        stukken.append("")

    if feature.testnamen:
        stukken.append("## Getest gedrag\n")
        for tn in feature.testnamen:
            stukken.append(f"- {testnaam_naar_zin(tn)}")
        stukken.append("")

    if d.beslissingen:
        stukken.append("## Beslissingen\n")
        for b in d.beslissingen:
            stukken.append(f"- {b}")
        stukken.append("")

    tekst = "\n".join(stukken).rstrip() + "\n"
    return tekst


# --- CLI ------------------------------------------------------------------------


def _feature_dirs(alleen: str | None) -> list[Path]:
    if alleen:
        d = FEATURES_DIR / alleen
        if not d.is_dir():
            print(f"Feature '{alleen}' niet gevonden onder {FEATURES_DIR}", file=sys.stderr)
            sys.exit(2)
        return [d]
    return sorted([d for d in FEATURES_DIR.iterdir() if d.is_dir() and not d.name.startswith("_")])


def cmd_generate(alleen: str | None) -> int:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    for feature_dir in _feature_dirs(alleen):
        feature = parse_feature(feature_dir)
        doc = render(feature)
        (DOCS_DIR / f"{feature.naam}.md").write_text(doc)
        rel = (DOCS_DIR / f"{feature.naam}.md").relative_to(ROOT)
        print(f"Geschreven: {rel}")
    return 0


def cmd_check() -> int:
    docstring_fouten: list[str] = []
    diffs: list[str] = []
    for feature_dir in _feature_dirs(None):
        try:
            feature = parse_feature(feature_dir)
        except DocstringError as exc:
            docstring_fouten.append(str(exc))
            continue
        verwacht = render(feature)
        bestaand_pad = DOCS_DIR / f"{feature.naam}.md"
        bestaand = bestaand_pad.read_text() if bestaand_pad.exists() else ""
        if bestaand != verwacht:
            diff = "".join(
                difflib.unified_diff(
                    bestaand.splitlines(keepends=True),
                    verwacht.splitlines(keepends=True),
                    fromfile=f"{DOCS_DIR.relative_to(ROOT)}/{feature.naam}.md (op disk)",
                    tofile=f"{DOCS_DIR.relative_to(ROOT)}/{feature.naam}.md (verwacht)",
                )
            )
            diffs.append(f"\n{diff}")
    if docstring_fouten:
        print("Ontbrekende of onvolledige module-docstrings (feature-docs skill regel 1):", file=sys.stderr)
        for fout in docstring_fouten:
            print(f"  - {fout}", file=sys.stderr)
    if diffs:
        print("Feature-docs niet actueel — draai `python scripts/docs/genereer-feature-docs.py generate`:", file=sys.stderr)
        for d in diffs:
            print(d, file=sys.stderr)
    if docstring_fouten or diffs:
        return 1
    print("Alle feature-docs zijn actueel.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_gen = sub.add_parser("generate", help="Regenereer feature-docs")
    p_gen.add_argument("naam", nargs="?", help="Optioneel: één feature")
    sub.add_parser("check", help="Faal op drift (CI)")
    args = parser.parse_args()

    if args.cmd == "generate":
        return cmd_generate(args.naam)
    if args.cmd == "check":
        return cmd_check()
    return 2


if __name__ == "__main__":
    sys.exit(main())
