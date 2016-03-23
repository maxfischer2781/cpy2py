# CPy2Py #

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
Any pickle'able objects may be used as parameters.

### Current Limitations ###

Functions may not have side-effects.

Dispatching calls is a blocking action and not threadsafe.
