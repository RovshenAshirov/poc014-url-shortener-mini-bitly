CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

def encode(num: int) -> str:
    if num == 0:
        return CHARS[0]
    result = []
    while num:
        result.append(CHARS[num % 62])
        num //= 62
    return "".join(reversed(result))

def decode(code: str) -> int:
    return sum(CHARS.index(c) * (62 ** i) for i, c in enumerate(reversed(code)))
