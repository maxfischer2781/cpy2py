# - # Copyright 2016 Max Fischer
# - #
# - # Licensed under the Apache License, Version 2.0 (the "License");
# - # you may not use this file except in compliance with the License.
# - # You may obtain a copy of the License at
# - #
# - #     http://www.apache.org/licenses/LICENSE-2.0
# - #
# - # Unless required by applicable law or agreed to in writing, software
# - # distributed under the License is distributed on an "AS IS" BASIS,
# - # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# - # See the License for the specific language governing permissions and
# - # limitations under the License.
"""
Tools for creating proxies to objects
"""


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