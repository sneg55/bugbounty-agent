from pathlib import Path


class BlockCursor:
    def __init__(self, name: str, data_dir: str = "."):
        self._path = Path(data_dir) / f".last_block_{name}"

    def get_last_block(self) -> int:
        if self._path.exists():
            return int(self._path.read_text().strip())
        return 0

    def set_last_block(self, block: int):
        self._path.write_text(str(block))
