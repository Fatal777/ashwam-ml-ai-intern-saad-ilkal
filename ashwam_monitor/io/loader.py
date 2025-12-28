import json
from pathlib import Path
from typing import List, Dict, Tuple

from ..models.inputs import ParserOutput, JournalEntry, GoldLabel
from ..exceptions import DataLoadError


def load_jsonl(path: Path, model_class) -> Tuple[List, List[dict]]:
    """
    load jsonl file and validate with pydantic
    returns (valid_records, errors) so we can handle partial failures
    """
    if not path.exists():
        raise DataLoadError(str(path), "file not found")

    valid = []
    errors = []

    with open(path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
                record = model_class.model_validate(data)
                valid.append(record)
            except json.JSONDecodeError as e:
                errors.append({
                    "line": line_num,
                    "error": "bad json",
                    "details": str(e)
                })
            except Exception as e:
                errors.append({
                    "line": line_num,
                    "error": "validation failed",
                    "details": str(e)
                })

    return valid, errors


def load_parser_outputs(path: Path) -> Tuple[List[ParserOutput], List[dict]]:
    return load_jsonl(path, ParserOutput)


def load_journals(path: Path) -> Tuple[List[JournalEntry], List[dict]]:
    return load_jsonl(path, JournalEntry)


def load_gold_labels(path: Path) -> Tuple[List[GoldLabel], List[dict]]:
    return load_jsonl(path, GoldLabel)


def load_journals_as_dict(path: Path) -> Dict[str, str]:
    """quick lookup of journal_id -> text"""
    journals, _ = load_journals(path)
    return {j.journal_id: j.text for j in journals}
