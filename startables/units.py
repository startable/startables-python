import copy
import itertools
from abc import ABC, abstractmethod
from typing import NewType, Callable, Iterable, TypeVar
import numpy as np
import pandas as pd

Unit = NewType('Unit', str)  # TODO <-- Does having this placeholder type make sense? Or just use str?


# TODO Put units.py in its own package? It's completely independent from startables.py...

# TODO make UnitPolicyError class? Would make it easier for client code to catch specific errors.


T = TypeVar('T', float, np.ndarray, pd.Series)


class UnitConversion(ABC):
    # TODO Is it plausible that this ABC will ever be useful?
    """
    Governs the conversion of a quantity between two given units of measurement.
    One of these two units is designated the "reference" unit. Typical usage is to designate the
    more fundamental unit as "reference", e.g. m would be reference for mm.
    The other unit is designated the "source" unit.

    Preferred idiom is to give UnitConversion objects names of the form 'sourceunit_refunit_conv' e.g. 'km_m_conv', or similar.
    """

    @abstractmethod
    def __init__(self, src_unit: Unit, ref_unit: Unit):
        """
        Concrete class implementations of this may extend the signature with additional parameters.
        :param src_unit: Source (non-reference) unit.
        :param ref_unit: Reference unit.
        """
        self._src_unit = src_unit
        self._ref_unit = ref_unit

    @abstractmethod
    def to_ref(self, value_src: T) -> T:
        """
        Convert value to reference unit from source unit.
        """
        pass

    @abstractmethod
    def from_ref(self, value_ref: T) -> T:
        """
        Convert value from reference unit to source unit.
        TODO consider renaming to_src?
        """
        pass

    @abstractmethod
    def reverse(self) -> 'UnitConversion':
        """
        Convenience method to build a UnitConversion in which ref_unit and src_unit are swapped
        """
        pass

    def alias(self, src_unit_alias: Unit) -> 'UnitConversion':
        """
        Convenience method to build a UnitConversion that is identical to this one, except with a new source unit
        that is but an alias of the old source unit i.e. different names, but same underlying unit.
        Usage example:
        uc = UnitConversion(Unit('mm'), Unit('m'), ...)
        alias_uc = uc.alias(Unit('millimetre'))
        """
        new_self = copy.copy(self)
        new_self._src_unit = src_unit_alias
        return new_self

    @property
    def src_unit(self) -> Unit:
        return self._src_unit

    @property
    def ref_unit(self) -> Unit:
        return self._ref_unit

    def __ne__(self, other):
        return not self == other


class IdentityUnitConversion(UnitConversion):
    """
    For unit pairs that are each other's aliases, e.g. 'm' and 'metre', og '°C' and 'deg_C'.
    Values need no conversion.
    """

    def __init__(self, src_unit: Unit, ref_unit: Unit):
        super().__init__(src_unit, ref_unit)

    def to_ref(self, value_src):
        return value_src

    def from_ref(self, value_ref):
        return value_ref

    def reverse(self):
        return IdentityUnitConversion(src_unit=self._ref_unit, ref_unit=self._src_unit)

    def __eq__(self, other):
        return (self.ref_unit, self.src_unit) == (other.ref_unit, other.src_unit)

    def __repr__(self):
        return f"{self.__class__}, source unit '{self.src_unit}', ref unit '{self.ref_unit}'"


class ScaleUnitConversion(UnitConversion):
    """
    For unit pairs that are convertible via a simple scale factor multiplication, e.g. mm and m.
    In typical applications, the vast majority of unit conversions are of this type.
    """

    def __init__(self, src_unit: Unit, ref_unit: Unit, ref_per_src: float):
        """
        :param ref_per_src: How many times the reference unit fits in the source unit. Example: would be 1000 if src_unit is 'km' and ref_unit is 'm'.
        """
        super().__init__(src_unit, ref_unit)
        self.ref_per_src = ref_per_src

    def to_ref(self, value_src):
        return value_src * self.ref_per_src

    def from_ref(self, value_ref):
        return value_ref / self.ref_per_src

    def reverse(self):
        return ScaleUnitConversion(src_unit=self._ref_unit, ref_unit=self._src_unit,
                                   ref_per_src=1 / self.ref_per_src)

    def __eq__(self, other):
        return (self.ref_unit, self.src_unit, self.ref_per_src) == \
               (other.ref_unit, other.src_unit, other.ref_per_src)

    def __repr__(self):
        return f"{self.__class__}, source unit '{self.src_unit}', ref unit '{self.ref_unit}', " \
               f"ref per source factor: {self.ref_per_src}"


class AffineUnitConversion(UnitConversion):
    """
    For unit pairs that are convertible via a linear function. For example, degrees Celsius and kelvin.
    """

    def __init__(self, src_unit: Unit, ref_unit: Unit, slope: float, intercept: float):
        """
        value in ref_unit = value in src_unit * slope + intercept
        Examples:
        ref_unit | src_unit  | slope | intercept
        kelvin     Celsius       1      273.15
        Celsius    Fahrenheit   5/9     -32*5/9
        :param slope: Slope of linear conversion (number of ref_unit per src_unit)
        :param intercept: Intercept of linear conversion (ref_unit value when src_unit value is 0)
        """
        super().__init__(src_unit, ref_unit)
        self.slope = slope
        self.intercept = intercept

    def to_ref(self, value_src):
        return value_src * self.slope + self.intercept

    def from_ref(self, value_ref):
        return (value_ref - self.intercept) / self.slope

    def reverse(self):
        return AffineUnitConversion(src_unit=self._ref_unit, ref_unit=self._src_unit,
                                    slope=1 / self.slope, intercept=-self.intercept / self.slope)

    def __eq__(self, other):
        return (self.ref_unit, self.src_unit, self.slope, self.intercept) == \
               (other.ref_unit, other.src_unit, other.slope, other.intercept)

    def __repr__(self):
        return f"{self.__class__}, source unit '{self.src_unit}', ref unit '{self.ref_unit}', " \
               f"value_ref = value_src * {self.slope} + {self.intercept}"


class CustomUnitConversion(UnitConversion):
    """
    For unit pairs that are not convertible via the other UnitConversion implementations.
    The to and from functions must be explicitly provided.
    This could be used for e.g. logarithmic things such as decibels, seismic magnitude scales, ...
    """

    # TODO support unit aliases? Like '[C]', 'degC', 'deg C', '°C', 'Celsius',...

    def __init__(self, src_unit: Unit, ref_unit: Unit, to_ref_func: Callable[[float], float],
                 from_ref_func: Callable[[float], float]):
        """
        You must ensure that to_ref_func is the inverse of from_ref_func.
        Failure to do this will, in general, not raise any errors and is liable to fail silently.
        :param to_ref_func: Function that converts value in src units to value in ref units.
        :param from_ref_func: Function that converts value in ref units to value in src units.
        """
        super().__init__(src_unit, ref_unit)
        self.to_ref_func = to_ref_func
        self.from_ref_func = from_ref_func

    def to_ref(self, value_src):
        return self.to_ref_func(value_src)

    def from_ref(self, value_ref):
        return self.from_ref_func(value_ref)

    def reverse(self):
        return CustomUnitConversion(src_unit=self._ref_unit, ref_unit=self._src_unit,
                                    to_ref_func=self.from_ref_func, from_ref_func=self.to_ref_func)

    def __eq__(self, other):
        # That hack tho... figuring out whether two functions are "equal" by comparing their bytecode.
        # There will arguably be false negatives in the case of two slightly
        # different implementations of the same thing, e.g. lambda x:x+5*2+3 and lambda x:x+3+5*2
        # but just don't, ok?
        return (self.ref_unit, self.src_unit,
                self.to_ref_func.__code__.co_code, self.from_ref_func.__code__.co_code) == \
               (other.ref_unit, other.src_unit,
                other.to_ref_func.__code__.co_code, other.from_ref_func.__code__.co_code)

    def __repr__(self):
        return f"{self.__class__}, source unit '{self.src_unit}', ref unit '{self.ref_unit}', " \
               f"to_ref_func: {self.to_ref_func}\nfrom_ref_func: {self.from_ref_func}"


class UnitPolicy(ABC):
    """
    Governs the unit conversion of quantities.
    Contains:
    * A collection of UnitConversion, each governing the conversion between a pair of units
    * A set of default target units, and a set of relations indicating to which of these default target units
      any given source unit is to be converted.
      In practice, this is implemented as a dict[src_unit, default_target_unit].
      A typical usage is to have default target units be units considered as "reference" or "standard" units.
      Alternatively, the default target unit can be overridden if specified explicitly.
    """

    @abstractmethod
    def convert(self, value: T,
                from_unit: Unit, to_unit: Unit) -> T:
        """
        Converts a value from a (source) unit to another (target) unit.
        Source and target units:
         * must both have the same reference unit in this unit policy;
         * may be identical (i.e. trivial case of no conversion).
        :param value: Value given in the source unit.
        :param from_unit: Unit from which to convert (source unit).
        :param to_unit: Unit to which to convert (target unit).
        :return: Value converted to the target unit.
        """
        pass

    @abstractmethod
    def convert_to_ref(self, value: T, src_unit: Unit) -> T:
        """
        Converts a value from a source unit to its associated reference unit.
        :param value: Value given in the source unit.
        :param src_unit: Unit from which to convert (source unit).
        :return: Value converted to the reference unit.
        """
        pass

    @abstractmethod
    def ref_unit(self, src_unit: Unit) -> Unit:
        """
        Returns a unit's associated reference unit.
        """
        pass


class CustomUnitPolicy(UnitPolicy):
    """
    A UnitPolicy with the machinery required to build it manually from UnitConversions.
    """

    def __init__(self, unit_conversions: Iterable[UnitConversion], duplicates: str = 'raise'):
        """
        :param unit_conversions: The UnitConversions to be used in this UnitPolicy. It is forbidden to have a unit appear as a source unit in one UnitConversion and a reference unit in another (this would lead to ambiguity).
        :param duplicates: Determines behaviour if multiple UnitConversions are given for the same unit. If 'raise', raise a ValueError. If 'overwrite', later ones overwrite any existing.
        """
        valid_duplicates_values = ['overwrite', 'raise']
        if duplicates not in valid_duplicates_values:
            raise ValueError(f"duplicates: Expected one of {valid_duplicates_values}, got '{duplicates}'.")

        src_units = [uc.src_unit for uc in unit_conversions]

        if duplicates == 'raise':
            duplicate_units = set(u for u in src_units if src_units.count(u) > 1)
            if duplicate_units:
                raise ValueError(f"Conflicting conversions supplied for units: {duplicate_units}.")

        ref_units = {uc.ref_unit for uc in unit_conversions}

        dual_role_units = set(src_units).intersection(ref_units)
        if dual_role_units:
            raise ValueError(f"Supplied units have conflicting roles (both source and reference): {dual_role_units}")
            # TODO this can be relaxed a bit. A given unit can be both source and ref, if and only if it strictly points to itself in a single UnitConversion (typically an IdentityUnitConversion).

        # Here we auto-add all ref_units as source units with a IdentityUnitConversion to self.
        # This simplifies later logic (in convert method and elsewhere).
        self._unit_conversions = {uc.src_unit: uc for uc in itertools.chain(
            unit_conversions, (IdentityUnitConversion(ru, ru) for ru in ref_units))}

    def __iter__(self):
        """
        Returns the units that are present in this unit policy.
        """
        yield from self._unit_conversions

    def convert(self, value, from_unit: Unit, to_unit: Unit):
        ucs = self._unit_conversions
        # TODO Some room to optimize trivial and semi-trivial cases, e.g. when
        # * to_unit is same as from_unit
        # * to_unit (or from_unit) is same as ref unit.
        # Worth it?

        try:
            if ucs[from_unit].ref_unit == ucs[to_unit].ref_unit:
                # Both share same ref unit. First convert from from_unit to ref unit, then from ref unit to to_unit.
                return ucs[to_unit].from_ref(ucs[from_unit].to_ref(value))
            raise ValueError(f"Can't convert: '{from_unit}' and '{to_unit}' do not share same reference unit.")
        except KeyError as ke:
            if from_unit in ucs:
                raise ValueError(f"Unit '{to_unit}' not found in unit policy.") from ke
            if to_unit in ucs:
                raise ValueError(f"Unit '{from_unit}' not found in unit policy.") from ke
            raise ValueError(f"Units '{from_unit}' and '{to_unit}' not found in unit policy.") from ke

        # if from_unit in ucs:
        #     if to_unit in ucs:
        #         if ucs[from_unit].ref_unit == ucs[to_unit].ref_unit:
        #             # Both share same ref unit. First convert from from_unit to ref unit, then from ref unit to to_unit.
        #             return ucs[to_unit].from_ref(ucs[from_unit].to_ref(value))
        #         raise ValueError(f"Can't convert: '{from_unit}' and '{to_unit}' do not share same reference unit.")
        #     raise ValueError(f"Unit '{to_unit}' not found in unit policy.")
        # else:
        #     if to_unit in ucs:
        #         raise ValueError(f"Unit '{from_unit}' not found in unit policy.")
        #     raise ValueError(f"Units '{from_unit}' and '{to_unit}' not found in unit policy.")

    def convert_to_ref(self, value, src_unit: Unit):
        try:
            return self._unit_conversions[src_unit].to_ref(value)
        except KeyError:
            raise ValueError(f"Unit '{src_unit}' not found in unit policy.")

    def ref_unit(self, src_unit: Unit) -> Unit:
        try:
            return self._unit_conversions[src_unit].ref_unit
        except KeyError as ke:
            raise ValueError(f"Unit '{src_unit}' not found in unit policy.") from ke
        # if src_unit in self._unit_conversions:
        #     return self._unit_conversions[src_unit].ref_unit
        # raise ValueError(f"Unit '{src_unit}' not found in unit policy.")

    def can_convert(self, from_unit: Unit, to_unit: Unit) -> bool:
        """
        Check whether a conversion from from_unit to to_unit is supported by this unit policy.
        """
        ucs = self._unit_conversions
        return from_unit in ucs and to_unit in ucs and ucs[from_unit].ref_unit == ucs[to_unit].ref_unit
