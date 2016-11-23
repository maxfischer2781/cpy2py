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

Using Functions in CPy2Py
=========================

Functions are lightweight, callable cousing of objects:

* plain functions, behaving like :py:class:`object` instances
* :py:func:`~cpy2py.twinfunction`, behaving like :py:class:`~cpy2py.TwinObject`

Normal functions live separately in each twinterpreter, and passing them between twinterpreters creates clones.
A :py:func:`~cpy2py.twinfunction` can be passed around transparently;
unlike a :py:class:`~cpy2py.TwinObject`, this only affects its nature as being *callable*.
Other actions, such as assigning attributes, are not transparent across twinterpreters.
