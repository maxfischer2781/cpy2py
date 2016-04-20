Magic Keys and Reserved Attributes
==================================

To keep track of state across several processes, :py:mod:`cpy2py` uses magic elements.
Some of them are useful to manually define, some for introspection, and some only used internally.

Magic Keys for Manual Definition
--------------------------------

:py:attr:`cpy2py.TwinObject.__twin_id__`

:py:data:`cpy2py.kernel_state.TWIN_ID`

:py:data:`cpy2py.kernel_state.MASTER_ID`

Other Magic Keys
----------------

:py:envvar: __CPY2PY_TWIN_ID__

:py:envvar: __CPY2PY_MASTER_ID__

Internal Magic Keys
-------------------
