from pathlib import Path
from typing import Optional
from ..models import ActionResult

def read_file(path: str, encoding: str = "utf-8", max_bytes: Optional[int] = None, root_dir: Optional[str] = None) -> ActionResult:
    p = Path(path)
    if not p.is_absolute() and root_dir:
        p = Path(root_dir) / p
    p = p.resolve()
    try:
        if max_bytes is None:
            content = p.read_text(encoding=encoding, errors="replace")
        else:
            with p.open("rb") as f:
                data = f.read(max_bytes)
            content = data.decode(encoding, errors="replace")
        return ActionResult(success=True, data={"path": str(p), "content": content})
    except Exception as e:
        return ActionResult(success=False, error=str(e))

def create_file(path: str, content: str, encoding: str = "utf-8", overwrite: bool = True, root_dir: Optional[str] = None) -> ActionResult:
    p = Path(path)
    if not p.is_absolute() and root_dir:
        p = Path(root_dir) / p
    p = p.resolve()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and not overwrite:
            return ActionResult(success=False, error="File exists")
        p.write_text(str(content), encoding=encoding)
        return ActionResult(success=True, data={"path": str(p), "bytes": len(str(content).encode(encoding))})
    except Exception as e:
        return ActionResult(success=False, error=str(e))

def edit_file(path: str, old: str, new: str, encoding: str = "utf-8", count: Optional[int] = None, root_dir: Optional[str] = None) -> ActionResult:
    p = Path(path)
    if not p.is_absolute() and root_dir:
        p = Path(root_dir) / p
    p = p.resolve()
    try:
        text = p.read_text(encoding=encoding)
        occurrences = text.count(old) if old else 0
        if count is None:
            updated = text.replace(old, new)
            replaced = occurrences
        else:
            c = int(count)
            updated = text.replace(old, new, c)
            replaced = min(c, occurrences)
        p.write_text(updated, encoding=encoding)
        return ActionResult(success=True, data={"path": str(p), "replaced": replaced})
    except Exception as e:
        return ActionResult(success=False, error=str(e))

def get_file_tree(start_path: str = ".", max_depth: int = 2, root_dir: Optional[str] = None) -> ActionResult:
    p = Path(start_path)
    if not p.is_absolute() and root_dir:
        p = Path(root_dir) / p
    p = p.resolve()

    if not p.exists():
         return ActionResult(success=False, error=f"Path {p} does not exist")

    def _tree(path: Path, depth: int) -> list:
        if depth > max_depth:
            return []
        
        res = []
        try:
            for child in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
                if child.name.startswith("."):
                    continue
                
                info = {
                    "name": child.name,
                    "type": "dir" if child.is_dir() else "file"
                }
                if child.is_dir():
                    children = _tree(child, depth + 1)
                    if children:
                        info["children"] = children
                    elif depth < max_depth:
                         info["children"] = []
                res.append(info)
        except PermissionError:
            pass
        return res

    try:
        tree = _tree(p, 1)
        return ActionResult(success=True, data={"tree": tree})
    except Exception as e:
        return ActionResult(success=False, error=str(e))