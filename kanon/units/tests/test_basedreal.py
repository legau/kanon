import math as m
import operator as op
import warnings
from decimal import Decimal, InvalidOperation
from fractions import Fraction

import hypothesis
import pytest
from hypothesis import strategies as st
from hypothesis.core import given

from kanon.units import BasedReal, Historical, Sexagesimal
from kanon.units.radices import (EmptyStringException, IllegalBaseValueError,
                                 IllegalFloatError, TooManySeparators)


class TestRadix:

    def test_init(self):
        assert Sexagesimal(
            (1, 2, 31), (6,), sign=-1, remainder=Decimal('0.3')
        ).__repr__() == "-01,02,31 ; 06 |r0.3"

        # From float
        assert Sexagesimal.from_float(-0.016666666666666666, 2) == -Sexagesimal((0,), (1,))
        assert Sexagesimal.from_float(0.5, 4).equals(Sexagesimal("0; 30, 0, 0, 0"))
        with pytest.raises(TypeError):
            Sexagesimal.from_float("s", 1)

        # From int
        assert Sexagesimal.from_int(5, 2) == Sexagesimal(5)
        with pytest.raises(TypeError):
            Sexagesimal.from_int("s")

        # From Decimal
        assert Sexagesimal.from_decimal(Decimal(5), 2) == Sexagesimal(5)
        with pytest.raises(TypeError):
            Sexagesimal.from_decimal(5, 1)

        # From Fraction
        assert Sexagesimal.from_fraction(Fraction(5, 1)).equals(Sexagesimal(5))
        assert Sexagesimal.from_fraction(Fraction(5, 2)) == Sexagesimal("2;30")
        with pytest.raises(TypeError):
            Sexagesimal.from_fraction(5)

        # From str
        assert Sexagesimal("21,1,6,3;34") == Sexagesimal((21, 1, 6, 3), (34,))
        assert Sexagesimal("0,0,0,0;").equals(Sexagesimal(0))
        with pytest.raises(TypeError):
            Sexagesimal._from_string(5)
        with pytest.raises(EmptyStringException):
            Sexagesimal("")
        with pytest.raises(TooManySeparators):
            Sexagesimal("1;2;3")

        # From Sequence
        with pytest.raises(IllegalBaseValueError) as err:
            Sexagesimal((-6, 3), ())
        assert "should be in the range" in str(err.value)
        with pytest.raises(IllegalFloatError) as err:
            Sexagesimal((0.3, 5), (6, 8))
        assert "An illegal float" in str(err.value)

        # From BasedReal

        assert Sexagesimal(Historical("3;15"), 1).equals(Sexagesimal("3;15"))

        # From multiple ints
        with pytest.raises(ValueError):
            Sexagesimal(3, 5, remainder=Decimal(-5))
        with pytest.raises(ValueError):
            Sexagesimal(3, 5, remainder=0.6)

        # Incorrect parameters
        with pytest.raises(TypeError):
            BasedReal()
        with pytest.raises(ValueError):
            Sexagesimal(Decimal(5))
        with pytest.raises(ValueError):
            Sexagesimal("", "")
        with pytest.raises(ValueError):
            Sexagesimal("", "", "", "")
        with pytest.raises(TypeError):
            Sexagesimal(("a", 2), (1, 2))
        with pytest.raises(ValueError):
            Sexagesimal(1, sign=2)

    def test_get(self):
        s = Sexagesimal("1, 2, 30; 18, 12, 23")
        assert s[-2] == 1
        assert s[0] == 30
        assert s[1] == 18
        assert s[:] == (1, 2, 30, 18, 12, 23)
        assert s[:0] == (1, 2)
        assert s[3::-1] == (23, 12, 18, 30, 2, 1)
        assert s[-1:] == (2, 30, 18, 12, 23)
        assert s[-1:2] == (2, 30, 18)

        with pytest.raises(IndexError):
            s[100]
        with pytest.raises(TypeError):
            s["5"]

    def test_truncations(self):
        s = Sexagesimal("1, 2, 30; 18, 52, 23")
        assert round(s).equals(s)
        assert round(s, 1).equals(Sexagesimal("1,2,30;19"))
        assert s.truncate(1).equals(Sexagesimal("1,2,30;18"))
        assert s.truncate(100).equals(s)
        assert m.trunc(s) == 3750
        assert m.floor(s) == 3750
        assert m.ceil(s) == 3751
        assert m.floor(-s) == -3749
        assert m.ceil(-s) == -3750
        assert Sexagesimal(1, 2, 3).minimize_precision().equals(Sexagesimal(1, 2, 3))
        assert Sexagesimal("1, 2, 3; 0, 0").minimize_precision().equals(Sexagesimal(1, 2, 3))

    def test_misc(self):
        s = Sexagesimal(5)
        assert (s or 1) == 5
        assert not s.equals("5")
        assert s.to_fraction() == Fraction(5)

        assert s ** -1 == 1 / 5
        assert s ** 1 == s
        assert Sexagesimal(0) ** 1 == 0

        assert s > 4

        assert (s / 1).equals(s)
        assert (s / -1).equals(-s)
        with pytest.raises(ZeroDivisionError):
            s / 0

        assert Sexagesimal("1,0;2,30,1").subunit_quantity(1) == 3602

    def test_shift(self):
        s = Sexagesimal("20, 1, 2, 30; 0")
        assert (s >> 1).equals(Sexagesimal("20, 1, 2; 30, 0"))
        assert (s << 1).equals(Sexagesimal("20, 1, 2, 30, 0"))
        assert (s >> -1).equals(s << 1)
        assert (s >> 7).equals(Sexagesimal("0; 0, 0, 0, 20, 1, 2, 30, 0"))
        s = Sexagesimal((20,), (0, 2, 0), remainder=Decimal(0.5))
        assert (s << 2).equals(Sexagesimal((20, 0, 2), (0,), remainder=Decimal(0.5)))
        assert (s << 5).equals(Sexagesimal(20, 0, 2, 0, 30, 0))

    @given(st.integers(min_value=0, max_value=15), st.integers(min_value=0, max_value=15))
    def test_resize(self, x, y):
        s = Sexagesimal("1, 2, 3; 30, 25")
        assert s.resize(x) == s
        resized = s.resize(x).resize(y)
        assert m.isclose(resized, s)
        assert resized.significant == y

    @given(st.floats(allow_infinity=False, allow_nan=False))
    def test_comparisons(self, x):
        s = Sexagesimal("1, 2; 30")
        xs = Sexagesimal.from_float(x, 1)
        for comp in (op.lt, op.le, op.eq, op.ne, op.ge, op.gt):
            if comp(float(s), x):
                assert comp(s, xs)
            else:
                assert not comp(s, xs)

    def biop_testing(self, x, y, operator):
        fx, fy = float(x), float(y)
        a = float(operator(x, y))
        b: float = operator(fx, fy)
        try:
            abstol = 1e-11 if a and b else 1e-09
            assert m.isclose(a, b.real, abs_tol=abstol)
            a = float(operator(x, fy))
            b = float(operator(fx, y))
            assert m.isclose(a, b.real, abs_tol=abstol)
        except Exception as e:
            hypothesis.note(f"{operator.__name__}: {a} {b}")
            raise e

    @given(st.from_type(Sexagesimal),
           st.from_type(Sexagesimal))
    def test_operations_with_remainders(self, x, y):
        fx = float(x)

        assert float(-x) == -fx
        assert float(+x) == fx
        assert abs(x) == abs(fx)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for o in (op.mul, op.add, op.sub):
                self.biop_testing(x, y, o)

        if y != 0:
            try:
                self.biop_testing(x, y, op.truediv)
            except InvalidOperation:
                pass

    @given(st.from_type(Sexagesimal),
           st.from_type(Sexagesimal))
    def test_operations_without_remainders(self, x, y):
        x, y = x.truncate(), y.truncate()
        fy = float(y)

        for o in (op.mul, op.add, op.sub, op.pow):
            if o == op.pow and (fy < 0 or fy > 10):
                continue
            self.biop_testing(x, y, o)

        if y != 0:
            self.biop_testing(x, y, op.truediv)

    @given(st.integers(min_value=int(-1e15), max_value=int(1e15)).map(Sexagesimal.from_int),
           st.integers(min_value=int(-1e15), max_value=int(1e15)).filter(lambda x: x != 0).map(Sexagesimal.from_int))
    def test_mod_integers(self, x, y):
        hypothesis.assume(int(x) % int(y) == float(x) % float(y))
        self.biop_testing(x, y, op.mod)
        self.biop_testing(x, y, op.floordiv)

    def test_mixed(self):

        h = Historical("11r 7s 29; 45")

        assert h == 4199.75

        assert (h >> 1).equals(Historical("1r 1s 18; 58, 45"))
        assert (h >> 2).equals(Historical("1s 3; 36, 58, 45"))
        assert (h << 1).equals(Historical("116r 10s 10; 30"))

        assert Historical("1s 3; 36, 58").__str__() == "1s 03 ; 36,58"
