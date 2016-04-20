.. # - # Copyright 2016 Max Fischer
.. # - #
.. # - # Licensed under the Apache License, Version 2.0 (the "License");
.. # - # you may not use this file except in compliance with the License.
.. # - # You may obtain a copy of the License at
.. # - #
.. # - #     http://www.apache.org/licenses/LICENSE-2.0
.. # - #
.. # - # Unless required by applicable law or agreed to in writing, software
.. # - # distributed under the License is distributed on an "AS IS" BASIS,
.. # - # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
.. # - # See the License for the specific language governing permissions and
.. # - # limitations under the License.

Using Objects in CPy2Py
=======================

There are two types of objects as far as CPy2Py is concerned:

* plain classes derived from :py:class:`object`
* twin classes derived from :py:class:`TwinObject`

The difference is in how objects behave when passed between twinterpreters.
Plain objects are *copied* (pass-by-value), while twin objects preserve their identity (pass-by-object/reference).
Since the former is not how Python usually handles objects, this may lead to unexpected side-effects.

Working with :py:class:`TwinObject`
-----------------------------------

CPy2Py's baseclass :py:class:`TwinObject` behaves like :py:class:`object` whenever possible.
Both are meant to be used as the baseclass for custom classes.
When not using twinterpreters, the two lead to the same behaviour.

.. code:: python

    class RegularObject(object):
        def foo(self):
            return 2

    class CPy2PyObject(TwinObject):
        def foo(self):
            return 2

The difference is that twin classes are aware of twinterpreters.
They have a *native twinterpreter*, in which they exist as defined.
In any other twinterpreter, they automatically resolve to a *twin proxy*.

.. code:: python

    class PyPyObject(TwinObject):
        __twin_id__ = 'pypy'  # makes class native to pypy twinterpeter

        # regular class definition
        def foo(self):
            return 2

The proxy acts as a transparent replacement for the native class and instances.
Native objects and proxies can be safely created, passed around and manipulated.
The underlying hooks of CPy2Py ensure that behaviour appears the same in any twinterpeter.

.. code:: python

    my_instance = CPy2PyObject()  # create native object or proxy transparently
    my_instance.foo()  # return 2
    my_instance.bar = 2  # add attribute, visible to native object and all proxies

The native Twinterpeter
^^^^^^^^^^^^^^^^^^^^^^^

Any class derived from :py:class:`TwinObject` is native to only one twinterpreter.
This is where its instances actually "live", i.e. where data are kept and methods executed.
All other twinterpreters just use proxies to the live instances.

A class' native twinterpeter is set via the class' attribute `__twin_id__`.
It can be a string, in which case it must name a twinterpeter, e.g. `"pypy"` or `"python"`.
Alternatively, it can be a magic CPy2Py key, e.g. to always use the main twinterpeter.
The corresponding twinterpeter must be running whenever an instance is created or used.

Working with :py:class:`object`
-------------------------------

Using plain :py:class:`object` classes with CPy2Py is fine in principle.
They will behave as usual and may be used in any twinterpeter.
Their behaviour is only affected when they are explicitly or implicitly passed between twinterpreters.

.. code:: python

    class TranslatorObject(TwinObject):
        __twin_id__ = 'pypy'  # makes class native to pypy twinterpeter

        def make_str(self, other):  # other is passed implicitly to native twinterpeter
            return '%s got %s' % (self, other)

        def pass_on(self, other):
            return other  # other is passed on twice, possibly creating a different object

        def insert_at(self, other, item, at):
            other[at] = item  # modify cloned other inplace
            return other  # return modified clone

CPy2Py must serialize and de-serialize objects to pass them between twinterpeters.
The side effects of this depend on the object.
Mostly, this is dictated by whether an object can be manipulated inplace.
In addition, passing objects back and forth creates clones.

Limitation of :py:class:`object`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

*Immutable types*, such as :py:class:`int` or :py:class:`frozenset`, will transition gracefully.
The most notable effect is that identity may be violated.
In the following example, the last assert will fail.

.. code:: python

    translator = TranslatorObject()
    test_int = 5
    test_set = frozenset((1,2,3))
    assert test_int == translator.pass_on(test_int), "Value comparison works"
    assert test_set == translator.pass_on(test_set), "Member value comparison works"
    assert test_int is translator.pass_on(test_int), "Primitives are singleton'ish"
    assert test_set is translator.pass_on(test_set), "Collections are singleton'ish"  # raises AssertionError

*Mutable types*, such as :py:class:`list` or many custom classes, will misbehave when mutated.
If not mutated, a properly written class (and all native types) behave like immutable types.
In the following example, a :py:class:`list` is mutated;
this does not propagate to the original object.

.. code:: python

    translator = TranslatorObject()
    test_list = [1,2,3]
    assert test_list == translator(test_list), "Member value comparison"
    cloned_list = translator.pass_on(test_list)
    inserted_list = translator.insert_at(test_list, 0, 0)
    test_list[0] = 0
    assert test_list == inserted_list, "Modifications are consistent"
    assert test_list == translator.pass_on(test_list), "Nested passing is consistent"
    assert test_list == cloned_list, "Mutations are transparent"  # raises AssertionError
