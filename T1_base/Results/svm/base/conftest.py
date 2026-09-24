import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
_own_dir = (_here / "../../../Public_Proyects/svm").resolve()
_parent_dir = (_here / "../../../Public_Proyects").resolve()

for _p in (str(_parent_dir), str(_own_dir)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    __import__("svm")
except Exception:
    pass
