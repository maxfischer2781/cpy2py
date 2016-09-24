import random

from .compat import rangex


_UPPERCASE_ORD = (ord('A'), ord('Z'))
_LOWERCASE_ORD = (ord('a'), ord('z'))


def random_str(length=16, upper_chars=0.5):
    return ''.join(
        chr(random.randint(*_UPPERCASE_ORD) if random.random() < upper_chars else random.randint(*_LOWERCASE_ORD))
        for _ in
        rangex(length)
    )
