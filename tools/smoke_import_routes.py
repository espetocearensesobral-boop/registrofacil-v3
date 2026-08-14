import importlib
import pkgutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
packages = ["routes", "utils"]
excluded = set()
loaded = []
skipped = []
for package_name in packages:
    package = importlib.import_module(package_name)
    for module_info in pkgutil.iter_modules(package.__path__, package_name + "."):
        if module_info.name in excluded:
            skipped.append(module_info.name)
            continue
        importlib.import_module(module_info.name)
        loaded.append(module_info.name)
print(f"smoke_import_routes: OK ({len(loaded)} módulos); ignorados: {', '.join(skipped) or 'nenhum'}")
