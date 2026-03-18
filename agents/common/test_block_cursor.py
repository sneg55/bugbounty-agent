import tempfile
from common.block_cursor import BlockCursor


def test_cursor_default_zero():
    with tempfile.TemporaryDirectory() as d:
        c = BlockCursor("test", d)
        assert c.get_last_block() == 0


def test_cursor_persists():
    with tempfile.TemporaryDirectory() as d:
        c = BlockCursor("test", d)
        c.set_last_block(42)
        c2 = BlockCursor("test", d)
        assert c2.get_last_block() == 42
