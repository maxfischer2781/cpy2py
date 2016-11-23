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

Definitions and Terms
=====================
.. glossary::

    Twins
        Twins are a group of entities created from the same code.
        Each twin appears and acts indistinguishable from its siblings.
        Together, they represent a single logical entity.

    Twinterpreters
        A group of interpreters acting as one to run a single program.
        Each twinterpreter runs only a portion of the program.
        However, the twinterpreters interact to create a single runtime environment.

    Twin Object
        Twins representing an entire :py:class:`object` as their logical entity.
        In each twinterpreter, at least one TwinObject exists for a given :py:class:`object`.
        Each TwinObject exposes the same attributes, methods and features as its siblings.
        However, there is only one :term:`Native Twin` representing the actual object.
        All other twins are :term:`Proxy Twin`s.

    Native Twin
        The twin holding the actual data and methods of a :term:`Twin Object` group.
        It is native to a twinterpreter, which stores its data and executes code.
        For the most part, the :term:`Native Twin` acts like a regular :py:class:`object`.
        However, it is known to its :term:`Proxy Twin`s and lives as long as any :term:`Proxy Twin` is alive.

    Proxy Twin
        A twin taking the place of a :term:`Native Twin` in a non-native twinterpreter.
        When interacting with a :term:`Proxy Twin`, those actions are implicitly relayed to the :term:`Native Twin`.
        Client code need not care about the nature of a :term:`Proxy Twin` - it is a full-fledged paceholder of its twin.

    twinfunction
        A lightweight relative of :term:`Twin Object` for callables.
        Calling a :term:`twinfunction` follows the same semantics as any operation on a :term:`Twin Object`.

    kernel
        The underlying connection between two :term:`twinterpreter`.
        Each kernel handles the communication at process level, and provides delegation of primitive commands.
