Describing Logic
================

Logic Values
------------

.. py:module:: rattle.bitvec

Rattle uses a three-valued logic with the values ``True``, ``False`` and a
third don't know value :data:`X`.
It is often necessary to operate on fixed width vectors of such logic values.
Rattle provides a :class:`BitVec` type for this.
The :data:`X` value, the :class:`BitVec` type and corresponding utility
functions are provided by the :mod:`rattle.bitvec` module.

.. autodata:: X
.. autoclass:: XClass

    .. automethod:: __eq__
    .. automethod:: __bool__

.. autofunction:: xbool
.. autofunction:: xnot

.. autoclass:: BitVec

    .. autoattribute:: width
    .. autoattribute:: value
    .. autoattribute:: mask
    .. automethod:: __init__
    .. automethod:: __eq__
    .. automethod:: same_as
    .. automethod:: concat
    .. automethod:: repeat
    .. automethod:: extend
    .. automethod:: sign_extend
    .. automethod:: sign_wrap
    .. automethod:: arith_rshift
    .. automethod:: updated_at
    .. automethod:: combine
    .. automethod:: values

.. autofunction:: bv
