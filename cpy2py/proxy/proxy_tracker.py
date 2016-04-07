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
Registration, tracking and lookup tools matching instances of the same logical
object in separate twinterpeters with each other.
"""
import weakref
import sys

from cpy2py.utility.compat import pickle

#: instances of twin objects or proxies currently alive in this twinterpeter
__active_instances__ = weakref.WeakValueDictionary()
__active_classes__ = weakref.WeakValueDictionary()


# pickling for inter-twinterpeter communication
def persistent_twin_id(obj):
    """Twin Pickler for inter-twinterpeter communication"""
    try:
        # twin object or proxy
        __import_mod_name__ = obj.__import_mod_name__
        # twin meta class
        if isinstance(obj, type):
            raise AttributeError
    except AttributeError:
        # regular object, let pickle do the work
        return None
    else:
        # twin object, only send reference
        return '%s\t%s\t%s\t%s' % (
            obj.__instance_id__,
            obj.__twin_id__,
            __import_mod_name__[0],
            __import_mod_name__[1]
        )


def persistent_twin_load(persid):
    """Twin Loader for inter-twinterpeter communication"""
    instance_id, twin_id, module_name, class_name = persid.split('\t')
    try:
        return __active_instances__[twin_id, instance_id]
    except KeyError:
        # twin object always exists - persid is enough for creating new proxies
        try:
            return __active_classes__[module_name, class_name](__twin_id__=twin_id, __instance_id__=instance_id)
        except KeyError:
            # __import__('foo.bar.baz') will only return 'foo'!
            __import__(module_name)
            module = sys.modules[module_name]
            klass = getattr(module, class_name)
            __active_classes__[module_name, class_name] = klass
            return klass(__twin_id__=twin_id, __instance_id__=instance_id)


def twin_pickler(*args, **kwargs):
    """Create a Pickler capable of handling twins"""
    pickler = pickle.Pickler(*args, **kwargs)
    pickler.persistent_id = persistent_twin_id
    return pickler


def twin_unpickler(*args, **kwargs):
    """Create an Unpickler capable of handling twins"""
    unpickler = pickle.Unpickler(*args, **kwargs)
    unpickler.persistent_load = persistent_twin_load
    return unpickler
