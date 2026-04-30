import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.core.base62 import encode, decode

def test_encode_basic():
    assert encode(1000000) == "4C92"

def test_encode_zero():
    assert encode(0) == "0"

def test_decode_basic():
    assert decode("4C92") == 1000000

def test_encode_decode_roundtrip():
    for n in [1, 100, 9999, 1000000, 56000000000]:
        assert decode(encode(n)) == n

def test_short_length():
    # 6 belgili kod 56 milliard gacha yetadi
    assert len(encode(1000000)) <= 6
    assert len(encode(56000000000)) <= 7
