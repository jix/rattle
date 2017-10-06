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

Rattle comes with a type system for signal values.
Signal types are *instances* of the :class:`SignalType` class.
Subclasses of :class:`SignalType` represent a family of related types.
For each subclass of :class:`SignalType` there is a corresponding subclass of
:class:`rattle.signal.Signal` that extends the supported operations on signals
of such a type.

The following signal types are built in:

*   ``Bool``, a single bit.
*   ``Bits(width)``, a fixed width vector of bits.
*   ``UInt(width)``, a fixed width unsigned integer.
*   ``SInt(width)``, a fixed width signed integer.
*   ``Vec(length, element_type)``, a fixed length vector containing elements of
    another type.
*   ``Bundle(...)``, an aggregate of multiple signals.
*   ``Enum(...)``, a set of possible values, each optionally with bundled
*   ``Clock(...)``, a clock signal with an optional bundled reset and enable
    signal.
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

Bool
^^^^

.. py:module:: rattle.type.bool

:data:`Bool` is the simplest signal type.
It consists of only a single bit.

.. autodata:: Bool
.. autoclass:: BoolType

Signals of the signal type :data:`Bool` are instances of :class:`BoolSignal` a
subclass of :class:`rattle.signal.Signal`.

.. autoclass:: BoolSignal()

    .. automethod:: repeat

Bits, UInt and SInt
^^^^^^^^^^^^^^^^^^^

Rattle differentiates between fixed-width integers (:class:`rattle.type.int.Int`)
and uninterpreted bit-vectors (:class:`rattle.type.bits.Bits`).
Operations on integers always return a signal of a large enough type to
represent all possible results.
They also truncate silently when assigning to shorter integer or bit-vector
signals.
In combination this means that you don't have to worry about unexpected
truncations within an expression, but also don't have to litter your code with
lots of explicit truncations.
Bit-vectors never silently truncate.

.. py:module:: rattle.type.bits

As fixed-width integers and bit-vectors share a lot of properties and
operations, there is a common superclass for both signal types:
:class:`BitsLike`.

.. autoclass:: BitsLike

    .. autoattribute:: width

.. autoclass:: BitsLikeSignal()

    .. autoattribute:: width
    .. automethod:: concat
    .. automethod:: extend
    .. automethod:: truncate
    .. automethod:: resize
    .. automethod:: repeat


Bit-vectors use the signal type :class:`Bits`.

.. autoclass:: Bits

    .. automethod:: concat

.. autoclass:: BitsSignal()

    .. automethod:: arith_rshift
    .. automethod:: as_uint
    .. automethod:: as_sint

.. py:module:: rattle.type.int

Fixed-width integers come in signed and unsigned forms.
Signed integers use the signal type :class:`SInt`, unsigned integers use
:class:`UInt`.
Both have a common superclass :class:`Int`.

.. autoclass:: Int

    .. autoattribute:: signed
    .. autoattribute:: min_value
    .. autoattribute:: max_value
    .. automethod:: from_value_range

.. autoclass:: IntSignal()

    .. automethod:: as_bits

.. autoclass:: UInt
.. autoclass:: UIntSignal()

    .. method:: extend(width)

        Add zero bits on the MSB side.

.. autoclass:: SInt
.. autoclass:: SIntSignal()

    .. method:: extend(width)

        Add copies of the sign bit on the MSB side.

Vec
^^^

.. py:module:: rattle.type.vec

The :class:`Vec` signal type represents a fixed length homogeneous vector, i.e.
several signals of the same signal type.
It can be used to describe memories (ROM and RAM).
Vector signals can be explicitly constructed using the :func:`vec` helper.

.. autoclass:: Vec

    .. automethod:: __init__
    .. autoattribute:: element_type
    .. autoattribute:: length

.. autoclass:: VecSignal

    .. autoattribute:: element_type

.. autofunction:: vec

.. autoclass:: VecHelper
