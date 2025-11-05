from typing import Callable, Dict, List
from sqlalchemy.orm import Session

SeederFn = Callable[[Session], None]
REGISTRY: Dict[str, SeederFn] = {}

def register(name: str):
    def deco(fn: SeederFn):
        REGISTRY[name] = fn
        return fn
    return deco

def list_seeders() -> List[str]:
    return sorted(REGISTRY.keys())

def run_selected(db: Session, names: List[str]):
    for n in names:
        fn = REGISTRY.get(n)
        if not fn:
            print(f"[seed] Skipping unknown: {n}")
            continue
        print(f"[seed] Running: {n}")
        fn(db)
