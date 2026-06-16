from pathlib import Path
import csv
import json
from typing import Any, Dict, List


def load_companies(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return [row for row in reader]


def load_mock_responses(json_path: Path) -> Dict[str, Any]:
    with json_path.open("r", encoding="utf-8") as json_file:
        return json.load(json_file)
