"""
To create a new `Calendar` you need to subclass it, then instanciate it with an `Era`.
A `Calendar` subclass has to have a name, a list of `Month` and an intercalation
method to be valid.

>>> class NewCal(Calendar):
...     _name = "My New Calendar"
...     _months = [Month(31, 32, "FirstMonth"),
...                Month(20, 22, "SecondMonth"),
...                Month(50, name="ThirdMonth")]
...     def intercalation(self, year: int) -> bool:
...         return year % 7 == 0
>>> my_era = Era("MyEra", 1234)
>>> my_calendar = NewCal(my_era)
>>> my_date = Date(my_calendar, (26, 3, 42))
>>> str(my_date)
'42 ThirdMonth 26 MyEra in My New Calendar'
>>> my_date.jdn
3851
"""

import abc
from dataclasses import dataclass, field
from functools import cached_property, lru_cache
from numbers import Real as _Real
from typing import Callable, Dict, List, Optional, Tuple, Union

from astropy.time import Time

from kanon.utils.types.number_types import Real

CALENDAR_REGISTRY: Dict[str, "Calendar"] = {}

__all__ = ("Julian", "Byzantine", "Arabic", "Persian", "Egyptian", "Month", "Era")


@dataclass(frozen=True)
class Era:
    """
    Dataclass defining an era.

    >>> Era("A.D.", 1721424)
    Era(name='A.D.', epoch=1721424)

    :param name: Name of the era
    :param days_ly: Start of the era in Julian Day Number
    """
    name: str
    epoch: float

    def days_from_epoch(self, jdn: float) -> float:
        return jdn - self.epoch


@dataclass(frozen=True)
class Month:
    """
    Dataclass defining a `~kanon.calendars.Calendar`'s month.

    >>> Month(28, 29, 'Februarius', ['February'])
    Month(days_cy=28, days_ly=29, name='Februarius', variant=['February'])

    :param days_cy: Number of days in a common year
    :param days_ly: Number of days in a leap year, optional, defaults to `days_cy` value
    :param name: Name of the month, optional, defaults to ""
    :param variant: List of name variants of this month, optional
    """

    days_cy: int

    days_ly: Optional[int] = None
    name: str = ""
    variant: Optional[List[str]] = None

    def _clone_new_leap(self, new_leap):
        return Month(self.days_cy, new_leap, self.name)

    def days(self, leap=False) -> int:
        """Returns the month's number of days in common or leap year

        :param leap: Is it a leap year, defaults to False
        :rtype: int
        """
        return self.days_ly if leap and self.days_ly else self.days_cy


@dataclass
class Date:
    """
    Dataclass defining a date.

    >>> cal = Calendar.registry["Julian A.D."]
    >>> date = Date(cal, (1,2,3))
    >>> str(date)
    '3 Februarius 1 A.D. in Julian'
    >>> date.jdn
    1721457
    >>> str(date + 1)
    '4 Februarius 1 A.D. in Julian'

    .. rubric:: Attributes

    .. autoattribute:: calendar
    .. autoattribute:: ymd
    .. autoattribute:: jdn
    """
    #: Calendar used in this date.
    calendar: "Calendar"
    #: Year, month and days, expressed in the specified calendar.
    ymd: Tuple[int, int, int]
    #: Date as a julian day number.
    jdn: float = field(init=False)

    def __post_init__(self):
        self.jdn = self.calendar.jdn_at_ymd(*self.ymd)

    def to_calendar(self, cal: "Calendar") -> "Date":
        """Express this date in another calendar.
        """
        return cal.from_julian_days(self.jdn)

    def days_from_epoch(self) -> float:
        """Get number of days from the start of the calendar
        """
        return self.jdn - self.calendar.era.epoch

    def to_time(self) -> Time:
        """Express this date as a `astropy.time.Time` object with ``jd`` format.
        """
        return Time(self.jdn, format="jd")

    def __add__(self, other: Union["Date", Real]) -> "Date":
        if not isinstance(other, (Date, _Real)):
            raise TypeError
        jdn: Real = other.jdn if isinstance(other, Date) else other
        return self.calendar.from_julian_days(self.jdn + jdn)

    def __sub__(self, other: Union["Date", Real]) -> "Date":
        if not isinstance(other, (Date, _Real)):
            raise TypeError
        jdn: Real = other.jdn if isinstance(other, Date) else other
        return self.calendar.from_julian_days(self.jdn - jdn)

    def __str__(self):
        year, month, days = self.ymd
        return (
            f"{days} {self.calendar.months[month-1].name} "
            f"{year} {self.calendar.era.name} in {self.calendar._name}"
        )


class Calendar(metaclass=abc.ABCMeta):
    """This abstract class defines calendar behaviors. You need to subclass this to
    create a working `Calendar`. You have to define its `interpolation` method, its `_name`,
    `_months` and maybe `_cycle`.
    """

    registry: Dict[str, "Calendar"] = CALENDAR_REGISTRY

    _name: str
    _months: List[Month]
    _era: Era
    _variant: str
    _cycle: Tuple[int, int] = (1, 0)

    def __new__(cls, era: Era, variant: str = "",
                months_mutation: Optional[Callable[[List[Month]], List[Month]]] = None):
        """
        :param era: Era used by this calendar.
        :type era: Era
        :param variant: Name of this variant, defaults to ""
        :type variant: str, optional
        :param months_mutation: Function transforming the Calendar class `months` list, defaults to None
        :type months_mutation: Optional[Callable[[List[Month]], List[Month]]], optional
        :raises ValueError: Raised when the calendar's name has already been used.
        """
        self = super().__new__(cls)
        self._era = era

        self._variant = variant

        if self.name in cls.registry:
            raise ValueError(
                f"{self.name} already exists in the registry, you might want to"
                "specify a variant name"
            )
        cls.registry[self.name] = self

        self._months = (months_mutation or (lambda x: x))(self._months.copy())
        return self

    @property
    def name(self):
        """Name of this calendar
        """
        return f"{self._name} {self._era.name}" + (f" {self._variant}" if self._variant else "")

    @property
    def months(self):
        """List of months
        """
        return self._months

    @property
    def cycle(self):
        """Cycle of common year and leap years (common, leap)
        """
        return self._cycle

    @property
    def era(self):
        return self._era

    @cached_property
    def common_year(self) -> int:
        """Number of days in a common year
        """
        return sum(m.days_cy for m in self.months)

    @cached_property
    def leap_year(self) -> int:
        """Number of days in a leap year
        """
        return sum(m.days(True) for m in self.months)

    @cached_property
    def cycle_length(self) -> int:
        """Number of days in a leap cycle
        """
        return self.cycle[0] * self.common_year + self.cycle[1] * self.leap_year

    @abc.abstractmethod
    def intercalation(self, year: int) -> bool:
        """Is the specified year an intercalation year (leap)
        """
        raise NotImplementedError

    @lru_cache
    def jdn_at_ymd(self, year: int, month: int, day: int) -> float:
        """Julian day number at the specified date in ymd
        """
        if 0 > month or month > len(self.months):
            raise ValueError(f"The month entered ({month}) is invalid 1..{len(self.months)}")
        mdn = self.months[month - 1].days(self.intercalation(year))
        if day > mdn or day < 1:
            raise ValueError(f"The day entered ({day}) is invalid in {self.months[month-1].name} 1..{mdn}")

        days = 0

        negative_year = year < 0

        if negative_year:
            year *= -1
            year += 1

        days += ((year - 1) // sum(self.cycle)) * self.cycle_length

        days += sum(
            self.leap_year if self.intercalation(y) else self.common_year
            for y in range(year - 1, year - 1 + (year - 1) % sum(self.cycle))
        )
        days += sum(
            m.days(self.intercalation(year)) for m in self.months[:month - 1]
        )

        days = days + day - 1

        if negative_year:
            days *= -1
            days -= 1

        return days + self.era.epoch

    def get_time(self, year: int, month: int, day: int) -> Time:
        """`astropy.time.Time` object at the specified date in ymd
        """
        return Time(self.jdn_at_ymd(year, month, day), format="jd")

    @lru_cache
    def from_julian_days(self, jdn: float) -> Date:
        """Builds a `Date` object at the specified julian day number.
        """
        year = int((self.era.days_from_epoch(jdn)) * sum(self.cycle) // self.cycle_length) + 1

        rem = jdn - self.jdn_at_ymd(year, 1, 1)
        for y in range(year, year + self.cycle_length):
            ylength = self.leap_year if self.intercalation(y) else self.common_year
            if rem >= ylength:
                rem -= ylength
                year += 1
            else:
                break

        leap = self.intercalation(year)
        for i, m in enumerate(self.months):
            if rem < m.days(leap):
                month = i + 1
                days = rem + 1
                break
            else:
                rem -= m.days(leap)

        return Date(self, (year, month, int(days)))

    def __repr__(self) -> str:
        return f"Calendar({self.name})"


class Julian(Calendar):
    _name = "Julian"
    _months = [
        Month(31, 31, 'Ianuarius', ['January']),
        Month(28, 29, 'Februarius', ['February']),
        Month(31, 31, 'Martius', ['March']),
        Month(30, 30, 'Aprilis', ['April']),
        Month(31, 31, 'Maius', ['May']),
        Month(30, 30, 'Iunius', ['June']),
        Month(31, 31, 'Iulius', ['July']),
        Month(31, 31, 'Augustus', ['August']),
        Month(30, 30, 'September', ['September']),
        Month(31, 31, 'October', ['October']),
        Month(30, 30, 'November', ['November']),
        Month(31, 31, 'December', ['December']),
    ]

    _cycle = (3, 1)

    def intercalation(self, year: int) -> bool:
        return year % 4 == 0


class Arabic(Calendar):
    _name = 'Arabic'
    _months = [
        Month(30, 30, 'Muḥarram'),
        Month(29, 29, 'Ṣafar'),
        Month(30, 30, 'Rabīʿ al-awwal'),
        Month(29, 29, 'Rabīʿ al-thānī'),
        Month(30, 30, 'Jumādā l-ūlā'),
        Month(29, 29, 'Jumādā l-thāniyya'),
        Month(30, 30, 'Rajab'),
        Month(29, 29, 'Shaʿbān'),
        Month(30, 30, 'Ramaḍān'),
        Month(29, 29, 'Shawwāl'),
        Month(30, 30, 'Dhū l-qaʿda'),
        Month(29, 30, 'Dhū l-ḥijja')
    ]
    _cycle = (19, 11)

    def intercalation(self, year: int) -> bool:
        return (1 + (year + 29) % 30) in {2, 5, 7, 10, 13, 16, 18, 21, 24, 26, 29}


class Byzantine(Calendar):
    _name = "Byzantine/Syrian"
    _months = [
        Month(31, 31, 'Adhār'),
        Month(30, 30, 'Nisān'),
        Month(31, 31, 'Ayyār'),
        Month(30, 30, 'Ḥazirān'),
        Month(31, 31, 'Tammūz'),
        Month(31, 31, 'Āb'),
        Month(30, 30, 'Aylūl'),
        Month(31, 31, 'Tishrīn al-awwal'),
        Month(30, 30, 'Tishrīn al-thānī'),
        Month(31, 31, 'Kānūn al-awwal'),
        Month(31, 31, 'Kānūn al-thānī'),
        Month(28, 29, 'Shubāṭ'),
    ]

    _cycle = (3, 1)

    def intercalation(self, year: int) -> bool:
        return (year - 1) % 4 == 0


class Egyptian(Calendar):
    _name = "Egyptian"
    _months = [
        Month(30, name='Thoth'),
        Month(30, name='Phaophi'),
        Month(30, name='Athyr'),
        Month(30, name='Choiak'),
        Month(30, name='Tybi'),
        Month(30, name='Mechir'),
        Month(30, name='Phamenoth'),
        Month(30, name='Pharmuthi'),
        Month(30, name='Pachon'),
        Month(30, name='Payni'),
        Month(30, name='Epiphi'),
        Month(30, name='Mesore'),
        Month(5, name='Epagomenai')
    ]

    def intercalation(self, year: int) -> bool:
        return False


class Persian(Calendar):
    _name = "Persian"
    _months = [
        Month(30, name='Farwardīn'),
        Month(30, name='Urdībihisht'),
        Month(30, name='Khurdādh'),
        Month(30, name='Tīr'),
        Month(30, name='Murdādh'),
        Month(30, name='Shahrīwar'),
        Month(30, name='Mihr'),
        Month(30, name='Ābān'),
        Month(30, name='Ādhar'),
        Month(30, name='Day'),
        Month(30, name='Bahman'),
        Month(30, name='Isfandārmudh'),
        Month(5, name='Andarjah')
    ]

    def intercalation(self, year: int) -> bool:
        return False


# Arabic Calendars
Arabic(Era("Civil Hijra", 1948440))
Arabic(Era("Astronomical Hijra", 1948439))

# Egyptian Calendars
Egyptian(Era("Nabonassar", 1448638))
Egyptian(Era("Philippus", 1603398))

_anno_domini = Era("A.D.", 1721424)

# Julian Calendars
Julian(_anno_domini)


def _leap_december(months):
    months[1] = months[1]._clone_new_leap(28)
    months[-1] = months[-1]._clone_new_leap(32)
    return months


Julian(_anno_domini, variant="Leap December", months_mutation=_leap_december)
Julian(_anno_domini, variant="First month March", months_mutation=lambda m: m[2:] + m[: 2])
Julian(Era("Julian Era", 0))

# Byzantine Calendars
Byzantine(_anno_domini)

# Persian Calendars
_yazdigird = Era("Yazdigird", 1952063)
Persian(_yazdigird, variant="Andarjah at the end")
Persian(_yazdigird, variant="Andarjah after Ābān", months_mutation=lambda m: m[: -1] + [m[-1]] + m[8: -1])
