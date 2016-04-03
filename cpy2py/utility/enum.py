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


__all__ = ['UniqueObj']


class UniqueObj(object):
    """
    Collectionless unique element

    This is a beautification of using :py:class:`object` as unique identifiers.
    It offers configurable str and repr for verbosity. In addition, it supports
    equality comparisons.
    """
    name = None

    class __metaclass__(type):
        def __new__(mcs, name, bases, class_dict):
            if class_dict.get('name') is None:
                class_dict['name'] = name
            return type.__new__(mcs, name, bases, class_dict)

        def __str__(cls):
            return cls.name

        def __repr__(cls):
            return "<unique object %s at 0x%x>" % (cls.__name__, id(cls))

        def __eq__(cls, other):
            return cls is other

        def __ne__(cls, other):
            return cls is not other

        def __gt__(cls, other):
            return NotImplemented

        def __lt__(cls, other):
            return NotImplemented

        def __ge__(cls, other):
            return NotImplemented

        def __le__(cls, other):
            return NotImplemented
