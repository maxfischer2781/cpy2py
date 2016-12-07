import unittest

from cpy2py.utility import proxy


def public_func(arg_a, arg_b, defargc=3, defarcb=4):
    """real_docstring"""
    pass


class TestExecutablePath(unittest.TestCase):
    def test_info(self):
        """Inherit informational attributes"""
        def proxy_func(*args, **kwargs):
            """proxy_docstring"""
            pass
        proxy.clone_function_meta(public_func, proxy_func)
        self.assertEqual(public_func.__doc__, proxy_func.__doc__)

    def test_lookup(self):
        """Inherit lookup attributes"""
        def proxy_func(*args, **kwargs):
            """proxy_docstring"""
            pass
        proxy.clone_function_meta(public_func, proxy_func)
        self.assertEqual(public_func.__module__, proxy_func.__module__)
        self.assertEqual(public_func.__name__, proxy_func.__name__)
        if hasattr(public_func, '__qualname__'):
            self.assertEqual(public_func.__qualname__, proxy_func.__qualname__)
