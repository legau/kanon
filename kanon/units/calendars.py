import abc
from dataclasses import dataclass
from functools import cached_property, lru_cache
from typing import Callable, Dict, List, Optional, Tuple

from astropy.time import Time

ERA_REGISTRY: Dict["Era", List["Calendar"]] = {}


CALENDAR_REGISTRY: Dict[str, "Calendar"] = {}


@dataclass(frozen=True)
class Era:
    name: str
    epoch: float

    def __post_init__(self):
        ERA_REGISTRY[self] = []

    def days_from_jdn(self, jdn: float) -> float:
        return jdn - self.epoch

    def _register_new_calendar(self, calendar: "Calendar"):
        ERA_REGISTRY[self].append(calendar)


@dataclass(frozen=True)
class Month:
    days_cy: int
    days_ly: Optional[int] = None
    name: str = ""
    variant: Optional[List[str]] = None

    def clone_new_leap(self, new_leap):
        return Month(self.days_cy, new_leap, self.name)

    def days(self, leap=False):
        return self.days_ly if leap and self.days_ly else self.days_cy


@dataclass
class Date:
    calendar: "Calendar"
    ymd: Tuple[int, int, int]

    def __post_init__(self):
        self.jdn = self.calendar.jdn_at_ymd(*self.ymd)

    def to_calendar(self, cal: "Calendar") -> "Date":
        return cal.from_julian_days(self.jdn)

    def to_time(self) -> Time:
        return Time(self.jdn, format="jd")

    def __str__(self):
        year, month, days = self.ymd
        return (
            f"{days} {self.calendar.months[month-1].name} "
            f"{year} {self.calendar.era.name} in {self.calendar.__class__.__name__}"
        )


class Calendar(metaclass=abc.ABCMeta):

    registry: Dict[str, "Calendar"] = CALENDAR_REGISTRY

    _name: str
    _months: List[Month]
    _era: Era
    _variant: str
    _cycle: Tuple[int, int] = (1, 0)

    def __new__(cls, era: Era, variant: str = "",
                months_mutation: Optional[Callable[[List[Month]], List[Month]]] = None):
        self = super().__new__(cls)
        self._era = era

        era._register_new_calendar(self)

        self._variant = variant

        if self.name in cls.registry:
            raise ValueError(f"{self.name} already exists in the registry")
        cls.registry[self.name] = self

        self._months = (months_mutation or (lambda x: x))(self._months.copy())
        return self

    @property
    def name(self):
        return f"{self._name} {self._era.name}" + (f" {self._variant}" if self._variant else "")

    @property
    def months(self):
        return self._months

    @property
    def cycle(self):
        return self._cycle

    @property
    def era(self):
        return self._era

    @cached_property
    def common_year(self) -> int:
        return sum(m.days_cy for m in self.months)

    @cached_property
    def leap_year(self) -> int:
        return sum(m.days(True) for m in self.months)

    @cached_property
    def cycle_length(self) -> int:
        return self.cycle[0] * self.common_year + self.cycle[1] * self.leap_year

    @abc.abstractmethod
    def intercalation(self, year: int) -> bool:
        raise NotImplementedError

    @lru_cache
    def jdn_at_ymd(self, year: int, month: int, day: int) -> int:
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
        return Time(self.jdn_at_ymd(year, month, day), format="jd")

    @lru_cache
    def from_julian_days(self, jdn: float) -> Date:
        year = int((jdn - self.era.epoch) * sum(self.cycle) // self.cycle_length) + 1

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
                return Date(self, (year, month, days))
            else:
                rem -= m.days(leap)

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
    months[1] = months[1].clone_new_leap(28)
    months[-1] = months[-1].clone_new_leap(32)
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