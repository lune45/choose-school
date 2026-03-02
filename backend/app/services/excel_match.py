from __future__ import annotations

import re
from difflib import SequenceMatcher
from io import BytesIO
from typing import Dict, List, Set, Tuple

import pandas as pd

from ..models import SchoolProgram


def _norm(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", text)
    return text


def _cell_texts(df: pd.DataFrame) -> List[str]:
    values: List[str] = []
    for row in df.itertuples(index=False):
        for cell in row:
            if cell is None:
                continue
            s = str(cell).strip()
            if not s or s.lower() in {"nan", "none"}:
                continue
            if 1 < len(s) <= 120:
                values.append(s)
    return values


def match_excel_schools(content: bytes, programs: List[SchoolProgram]) -> Tuple[List[int], List[str], List[str]]:
    school_to_ids: Dict[str, List[int]] = {}
    labels_by_id: Dict[int, str] = {}

    for p in programs:
        key = _norm(p.school_name)
        school_to_ids.setdefault(key, []).append(p.id)
        labels_by_id[p.id] = f"{p.school_name} - {p.program_name}"

    all_keys = list(school_to_ids.keys())

    matched_ids: Set[int] = set()
    matched_labels: Set[str] = set()
    unmatched_cells: Set[str] = set()

    xls = pd.ExcelFile(BytesIO(content))
    for sheet in xls.sheet_names:
        df = xls.parse(sheet_name=sheet, header=None)
        for raw_cell in _cell_texts(df):
            key = _norm(raw_cell)
            if len(key) < 3:
                continue

            exact_ids = school_to_ids.get(key)
            if exact_ids:
                for i in exact_ids:
                    matched_ids.add(i)
                    matched_labels.add(labels_by_id[i])
                continue

            best_key = ""
            best_score = 0.0
            for k in all_keys:
                ratio = SequenceMatcher(None, key, k).ratio()
                if ratio > best_score:
                    best_score = ratio
                    best_key = k

            if best_score >= 0.88 and best_key in school_to_ids:
                for i in school_to_ids[best_key]:
                    matched_ids.add(i)
                    matched_labels.add(labels_by_id[i])
            else:
                unmatched_cells.add(raw_cell)

    return sorted(matched_ids), sorted(matched_labels), sorted(unmatched_cells)[:50]
