# CPy2Py #
[![Code Issues](https://www.quantifiedcode.com/api/v1/project/fa44a076922a4047a736e29bb0a206f4/badge.svg)](https://www.quantifiedcode.com/app/project/fa44a076922a4047a736e29bb0a206f4)

## About ##

The purpose of CPy2Py is to leverage the advantages of different Python implementations.
Did you ever need the speed of pypy but also the extensions of cpython?
CPy2Py makes this possible in a single application.

## Overview ##

CPy2Py uses twinterpeters - additional, alternative interpeters running along the primary ones.
Function calls can be dispatched and objects may reside in either interpeter.
The package abstracts the mechanisms of this, allowing for an almost seamless interaction.

## Current State ##

The module currently allows dispatching arbitrary function calls.
Objects may be created and persist inside the twinterpeter.
Object attributes and methods can be accessed and used.
Any pickle'able objects may be used as parameters.

### Current Limitations ###

   * Functions may not have side-effects.

   * Dispatching calls is a blocking action and not threadsafe.

   * Proxy Objects used inline may be garbage collected pre-maturely. Use `instance = MyClass(); instance.do_stuff()` if there are problems with `MyClass().do_stuff()`

   * The native Twintepeter may not be changed when inheriting.
