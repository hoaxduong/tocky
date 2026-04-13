"""Fetch and upsert ICD-10 codes into the database.

Usage:
    cd apps/api

    # Seed English codes (default source)
    uv run python -m app.scripts.seed_icd10

    # Seed from a local CSV
    uv run python -m app.scripts.seed_icd10 --source /path/to/codes.csv

    # Import French CIM-10 descriptions (from official data)
    uv run python -m app.scripts.seed_icd10 --lang fr \\
        --source https://raw.githubusercontent.com/gr0g/CMA/master/cim10.csv \\
        --code-col diag_code --desc-col diag_libelle --delimiter ";"

    # Import from a simple two-column local file (code,description)
    uv run python -m app.scripts.seed_icd10 --lang vi \\
        --source /path/to/icd10_vi.csv \\
        --code-col 0 --desc-col 1

Known sources:
    en: https://raw.githubusercontent.com/kamillamagna/ICD-10-CSV/refs/heads/master/codes.csv
    fr: https://raw.githubusercontent.com/gr0g/CMA/master/cim10.csv
"""

import argparse
import asyncio
import csv
import io
import json

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

ICD10_EN_URL = (
    "https://raw.githubusercontent.com/kamillamagna/"
    "ICD-10-CSV/refs/heads/master/codes.csv"
)

ICD10_FR_URL = (
    "https://raw.githubusercontent.com/gr0g/"
    "CMA/master/cim10.csv"
)

# Built-in parsers for known sources
_KNOWN_SOURCES = {
    "en": {
        "url": ICD10_EN_URL,
        "code_col": 2,
        "desc_col": 3,
        "delimiter": ",",
        "has_header": False,
    },
    "fr": {
        "url": ICD10_FR_URL,
        "code_col": "diag_code",
        "desc_col": "diag_libelle",
        "delimiter": ";",
        "has_header": True,
    },
}


def _format_code(raw_code: str) -> str:
    """Normalize code: insert dot after 3rd char if missing."""
    raw = raw_code.strip()
    if len(raw) > 3 and "." not in raw:
        return f"{raw[:3]}.{raw[3:]}"
    return raw


async def _fetch_raw(source: str) -> str:
    """Fetch text from a URL or local file."""
    if not source.startswith("http"):
        with open(source) as f:
            return f.read()
    async with httpx.AsyncClient(timeout=60) as client:
        print(f"Fetching from {source} ...")
        resp = await client.get(source, follow_redirects=True)
        resp.raise_for_status()
        return resp.text


def _parse_csv(
    raw: str,
    code_col: int | str,
    desc_col: int | str,
    delimiter: str = ",",
    has_header: bool = False,
) -> list[tuple[str, str]]:
    """Parse CSV/TSV into (code, description) pairs.

    code_col/desc_col can be int (positional) or str (header name).
    """
    results: list[tuple[str, str]] = []
    reader = csv.reader(io.StringIO(raw), delimiter=delimiter)

    header: list[str] | None = None
    if has_header or isinstance(code_col, str):
        header = next(reader, None)
        if header:
            header = [h.strip().strip('"') for h in header]

    # Resolve column names to indices
    code_idx: int
    desc_idx: int
    if isinstance(code_col, str) and header:
        code_idx = header.index(code_col)
    else:
        code_idx = int(code_col)
    if isinstance(desc_col, str) and header:
        desc_idx = header.index(desc_col)
    else:
        desc_idx = int(desc_col)

    for row in reader:
        if len(row) <= max(code_idx, desc_idx):
            continue
        code = _format_code(row[code_idx])
        desc = row[desc_idx].strip().strip('"')
        if code and desc and len(code) >= 3:
            results.append((code, desc))

    return results


async def seed_english(source: str | None = None) -> None:
    """Seed English ICD-10 codes (default operation)."""
    cfg = _KNOWN_SOURCES["en"]
    raw = await _fetch_raw(source or cfg["url"])
    pairs = _parse_csv(
        raw,
        code_col=cfg["code_col"],
        desc_col=cfg["desc_col"],
        delimiter=cfg["delimiter"],
        has_header=cfg["has_header"],
    )
    if not pairs:
        print("No codes found in source data.")
        return

    print(f"Parsed {len(pairs)} English ICD-10 codes.")

    codes = [
        {
            "code": code,
            "description": desc,
            "descriptions": json.dumps({"en": desc}),
            "category": code[:3],
        }
        for code, desc in pairs
    ]

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as db:
        db: AsyncSession
        batch_size = 500
        total = 0
        for i in range(0, len(codes), batch_size):
            batch = codes[i : i + batch_size]
            await db.execute(
                text(
                    "INSERT INTO icd10_codes "
                    "(code, description, descriptions, category) "
                    "VALUES (:code, :description, "
                    "CAST(:descriptions AS json), :category) "
                    "ON CONFLICT (code) DO UPDATE SET "
                    "description = EXCLUDED.description, "
                    "descriptions = EXCLUDED.descriptions, "
                    "category = EXCLUDED.category"
                ),
                batch,
            )
            total += len(batch)
            if total % 5000 < batch_size:
                print(f"  Upserted {total}/{len(codes)} ...")

        await db.commit()
        print(f"Done. {total} codes upserted.")
    await engine.dispose()


async def import_language(
    lang: str,
    source: str | None,
    code_col: int | str,
    desc_col: int | str,
    delimiter: str,
) -> None:
    """Import descriptions for a specific language.

    Matches codes against existing rows and merges into
    the `descriptions` JSON column.
    """
    # Use known source config if available and no overrides
    known = _KNOWN_SOURCES.get(lang)
    if known and source is None:
        source = known["url"]
        code_col = known["code_col"]
        desc_col = known["desc_col"]
        delimiter = known["delimiter"]

    if source is None:
        print(
            f"No source specified for '{lang}'. "
            f"Use --source <url_or_file>."
        )
        return

    raw = await _fetch_raw(source)
    has_header = isinstance(code_col, str)
    pairs = _parse_csv(
        raw, code_col, desc_col, delimiter, has_header
    )
    if not pairs:
        print(f"No codes found for '{lang}'.")
        return

    print(f"Parsed {len(pairs)} {lang} descriptions.")

    # Build lookup: code -> description
    lang_descs = {code: desc for code, desc in pairs}

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as db:
        db: AsyncSession
        # Merge translations into descriptions JSON
        # Using jsonb_set to add the language key
        batch_size = 500
        total = 0
        items = list(lang_descs.items())
        for i in range(0, len(items), batch_size):
            batch = [
                {"code": code, "desc": desc}
                for code, desc in items[i : i + batch_size]
            ]
            await db.execute(
                text(
                    "UPDATE icd10_codes SET "
                    "descriptions = descriptions || "
                    "jsonb_build_object("
                    ":lang, CAST(:desc AS text)) "
                    "WHERE code = :code"
                ).bindparams(lang=lang),
                batch,
            )
            total += len(batch)
            if total % 5000 < batch_size:
                print(f"  Updated {total}/{len(items)} ...")

        await db.commit()
        print(f"Done. {total} {lang} descriptions imported.")

    await engine.dispose()


def _try_int(val: str) -> int | str:
    """Parse as int if numeric, else return as string (header name)."""
    try:
        return int(val)
    except ValueError:
        return val


def main():
    parser = argparse.ArgumentParser(
        description="Seed ICD-10 codes into the database"
    )
    parser.add_argument(
        "--lang",
        default=None,
        help=(
            "Language to import (e.g. fr, vi, ar). "
            "Omit to seed English codes. "
            "Built-in configs exist for: en, fr."
        ),
    )
    parser.add_argument(
        "--source",
        default=None,
        help="URL or local file path to CSV/TSV data.",
    )
    parser.add_argument(
        "--code-col",
        default=None,
        help=(
            "Column for ICD-10 code: integer index "
            "or header name (e.g. 0, diag_code)."
        ),
    )
    parser.add_argument(
        "--desc-col",
        default=None,
        help=(
            "Column for description: integer index "
            "or header name (e.g. 1, diag_libelle)."
        ),
    )
    parser.add_argument(
        "--delimiter",
        default=",",
        help='CSV delimiter (default: ",").',
    )
    args = parser.parse_args()

    async def run():
        if args.lang is None:
            # Default: seed English
            await seed_english(args.source)
        else:
            code_col: int | str = (
                _try_int(args.code_col)
                if args.code_col is not None
                else 0
            )
            desc_col: int | str = (
                _try_int(args.desc_col)
                if args.desc_col is not None
                else 1
            )
            await import_language(
                args.lang,
                args.source,
                code_col,
                desc_col,
                args.delimiter,
            )

    asyncio.run(run())


if __name__ == "__main__":
    main()
