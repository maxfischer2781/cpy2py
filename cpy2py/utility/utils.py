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


def clone_function_meta(real_func, wrap_func):
    """Clone the public metadata of `real_func` to `wrap_func`"""
    wrap_func.__wrapped__ = real_func
    for attribute in (
            '__doc__', '__twin_id__',
            '__signature__', '__defaults__',
            '__name__', '__module__',
            '__qualname__', '__annotations__'
    ):
        try:
            setattr(wrap_func, attribute, getattr(real_func, attribute))
        except AttributeError:
            if attribute in ('__name__', '__module__'):
                raise TypeError('Unable to inherit __module__.__name__ from %r to %r' % (real_func, wrap_func))
