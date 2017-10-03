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

Signal Types
------------

.. py:module:: rattle.type.type

Rattle comes with a type system for logic values.
Signal types are *instances* of the :class:`SignalType` class.
Subclasses of :class:`SignalType` represent a family of related types.

The following signal types are built in:

*   ``Bool``, a single bit.
*   ``Bits(width)``, a fixed width vector of bits.
*   ``UInt(width)``, a fixed width unsigned integer.
*   ``SInt(width)``, a fixed width signed integer.
*   ``Vec(length, element_type)``, a fixed length vector containing elements of
    another type.
*   ``Clock(...)``, a clock signal with an optional bundled reset and enable
    signal.
*   ``Bundle(...)``, an aggregate of multiple signals.
*   ``Enum(...)``, a set of possible values, each optionally with bundled
    signals.
*   ``Flip(signal_type)``, a wrapper that switches the direction of the
    contained type when used in the context of a module port.
*   ``Packed(signal_type)``, a wrapper that ensures the contained type is
    represented as a single bit vector for synthesis.
*   ``InOutType(width)``, used to represent bidirectional/tristate ports.
    These are not supported by Rattle, but this opaque placeholder type allows
    connecting non-Rattle interfaces that do.

.. autoclass:: SignalType

    .. autoattribute:: contains_flipped
    .. automethod:: convert
    .. automethod:: generic_convert
    .. automethod:: common
    .. automethod:: unpack
