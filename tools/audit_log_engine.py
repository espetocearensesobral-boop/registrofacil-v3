from __future__ import annotations

import ast
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {'.git', '__pycache__', '.pytest_cache', '.venv-build'}


def main() -> int:
    imports = Counter()
    calls = Counter()
    per_file = defaultdict(lambda: Counter())
    examples = defaultdict(list)
    for path in ROOT.rglob('*.py'):
        if any(part in SKIP for part in path.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        except (OSError, SyntaxError):
            continue
        rel = str(path.relative_to(ROOT))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in {'utils.logger', 'utils.logger_config'}:
                for alias in node.names:
                    key = f'{node.module}:{alias.name}'
                    imports[key] += 1
                    per_file[rel][key] += 1
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {'debug', 'info', 'warning', 'error', 'critical', 'exception'}:
                    owner = node.func.value.id if isinstance(node.func.value, ast.Name) else '<attribute>'
                    key = f'{owner}.{node.func.attr}'
                    calls[key] += 1
                    per_file[rel][key] += 1
                    if len(examples[key]) < 5:
                        examples[key].append(f'{rel}:{node.lineno}')

    report = {
        'imports': imports,
        'calls': calls,
        'files_using_legacy_logger_import': sorted(
            rel for rel, counters in per_file.items() if any(key.endswith(':logger') for key in counters)
        ),
        'files_using_domain_logger_import': sorted(
            rel for rel, counters in per_file.items() if any(':auth_logger' in key or ':operacional_logger' in key or ':sistema_logger' in key or ':manutencao_logger' in key for key in counters)
        ),
        'examples': examples,
    }
    serializable = {
        'imports': dict(report['imports']),
        'calls': dict(report['calls']),
        'files_using_legacy_logger_import': report['files_using_legacy_logger_import'],
        'files_using_domain_logger_import': report['files_using_domain_logger_import'],
        'examples': dict(report['examples']),
    }
    print(json.dumps(serializable, ensure_ascii=False, indent=2, default=dict))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
