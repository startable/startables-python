import math

from pytest import fixture, raises, approx

from startables.units import Unit, ScaleUnitConversion, AffineUnitConversion, \
    CustomUnitConversion, CustomUnitPolicy, IdentityUnitConversion


class TestIdentityUnitConversion:

    def test_eq(self):
        assert IdentityUnitConversion(Unit('metre'), Unit('m')) == IdentityUnitConversion(Unit('metre'), Unit('m'))
        assert IdentityUnitConversion(Unit('metre'), Unit('m')) != IdentityUnitConversion(Unit('mtr'), Unit('m'))

    def test_to_ref(self):
        assert IdentityUnitConversion(Unit('metre'), Unit('m')).to_ref(42) == 42

    def test_from_ref(self):
        assert IdentityUnitConversion(Unit('metre'), Unit('m')).from_ref(42) == 42

    def test_reverse(self):
        assert IdentityUnitConversion(Unit('metre'), Unit('m')).reverse() == \
               IdentityUnitConversion(Unit('m'), Unit('metre'))


class TestScaleUnitConversion:

    def test_eq(self):
        assert ScaleUnitConversion(Unit('mm'), Unit('m'), 0.001) == ScaleUnitConversion(Unit('mm'), Unit('m'), 0.001)
        assert ScaleUnitConversion(Unit('bs'), Unit('m'), 0.123) != ScaleUnitConversion(Unit('mm'), Unit('m'), 0.001)

    def test_to_ref(self):
        assert ScaleUnitConversion(Unit('mm'), Unit('m'), 0.001).to_ref(42) == 0.042

    def test_from_ref(self):
        assert ScaleUnitConversion(Unit('mm'), Unit('m'), 0.001).from_ref(42) == 42000

    def test_reverse(self):
        assert ScaleUnitConversion(Unit('mm'), Unit('m'), 0.001).reverse().to_ref(42) == approx(42000)

    def test_alias(self):
        alias = ScaleUnitConversion(Unit('mm'), Unit('m'), 0.001).alias(Unit('millimetre'))
        assert alias == ScaleUnitConversion(Unit('millimetre'), Unit('m'), 0.001)
        assert alias.to_ref(1000) == 1


class TestLinearUnitConversion:

    def test_eq(self):
        assert AffineUnitConversion(Unit('degC'), Unit('K'), 1, 273.15) == \
               AffineUnitConversion(Unit('degC'), Unit('K'), 1, 273.15)
        assert AffineUnitConversion(Unit('degC'), Unit('K'), 1, 273.15) != \
               AffineUnitConversion(Unit('degC'), Unit('K'), 1, 666)

    def test_to_ref(self):
        assert AffineUnitConversion(Unit('degC'), Unit('K'), 1, 273.15).to_ref(-273.15) == 0

    def test_from_ref(self):
        assert AffineUnitConversion(Unit('degC'), Unit('K'), 1, 273.15).from_ref(0) == -273.15

    def test_reverse(self):
        assert AffineUnitConversion(Unit('degC'), Unit('K'), 1, 273.15).reverse().to_ref(293.15) == approx(20)


class TestCustomUnitConversion:

    @fixture
    def custom_unit_conversion(self) -> CustomUnitConversion:
        return CustomUnitConversion(Unit('zonk'), Unit('bork'),
                                    lambda x: x ** 2,
                                    lambda x: math.sqrt(x))

    def test_eq(self, custom_unit_conversion):
        assert custom_unit_conversion == \
               CustomUnitConversion(Unit('zonk'), Unit('bork'), lambda x: x ** 2, lambda x: math.sqrt(x))
        assert custom_unit_conversion != \
               CustomUnitConversion(Unit('zonk'), Unit('bork'), lambda x: x ** 2, lambda x: x)

    def test_to_ref(self, custom_unit_conversion):
        assert custom_unit_conversion.to_ref(12) == 144

    def test_from_ref(self, custom_unit_conversion):
        assert custom_unit_conversion.from_ref(256) == 16

    def test_reverse(self, custom_unit_conversion):
        assert custom_unit_conversion.reverse() == \
               CustomUnitConversion(Unit('bork'), Unit('zonk'), lambda x: math.sqrt(x), lambda x: x ** 2)

    def test_alias(self, custom_unit_conversion):
        alias = custom_unit_conversion.alias(Unit('jiggyjag'))
        assert alias == CustomUnitConversion(Unit('jiggyjag'), Unit('bork'), lambda x: x ** 2, lambda x: math.sqrt(x))
        assert alias.to_ref(12) == approx(144)
        assert alias.from_ref(9) == approx(3)


class TestCustomUnitPolicy:

    def test_iter(self):
        cup = CustomUnitPolicy([
            ScaleUnitConversion(Unit('km'), Unit('m'), 1000),
            ScaleUnitConversion(Unit('mm'), Unit('m'), 0.001),
            AffineUnitConversion(Unit('C'), Unit('K'), 1, 273.15)])
        assert Unit('mm') in cup
        assert Unit('m') in cup
        assert set(cup) == {'km', 'mm', 'm', 'C', 'K'}

    def test_duplicate_raise(self):
        with raises(ValueError):
            CustomUnitPolicy([
                ScaleUnitConversion(Unit('km'), Unit('m'), 1000),
                ScaleUnitConversion(Unit('km'), Unit('mm'), 1000000)], duplicates='raise')

    def test_duplicate_overwrite(self):
        cup = CustomUnitPolicy([
            ScaleUnitConversion(Unit('km'), Unit('m'), 1000),
            ScaleUnitConversion(Unit('km'), Unit('mm'), 1000000)], duplicates='overwrite')
        assert cup.ref_unit(Unit('km')) == Unit('mm')

    def test_conflicting_roles(self):
        with raises(ValueError):
            CustomUnitPolicy([
                ScaleUnitConversion(Unit('m'), Unit('km'), 0.001),
                ScaleUnitConversion(Unit('km'), Unit('mm'), 1000000)], duplicates='overwrite')

    def test_convert(self):
        cup = CustomUnitPolicy([
            ScaleUnitConversion(Unit('km'), Unit('m'), 1000),
            ScaleUnitConversion(Unit('mm'), Unit('m'), 0.001),
            AffineUnitConversion(Unit('C'), Unit('K'), 1, -273.15)])
        assert cup.convert(42, Unit('km'), to_unit=Unit('m')) == 42000  # source to ref
        assert cup.convert(42, Unit('m'), to_unit=Unit('m')) == 42  # ref to ref
        assert cup.convert(42, Unit('m'), to_unit=Unit('km')) == 0.042  # ref to source
        assert cup.convert(42, Unit('km'), to_unit=Unit('mm')) == 42000000  # source to other source
        with raises(ValueError):
            cup.convert(42, Unit('km'), to_unit=Unit('K'))  # Don't share same ref unit
        with raises(ValueError):
            cup.convert(42, Unit('m'), to_unit=Unit('C'))  # Don't share same ref unit
        with raises(ValueError):
            cup.convert(42, Unit('m'), to_unit=Unit('bogus'))  # to_unit doesn't exist
        with raises(ValueError):
            cup.convert(42, Unit('bogus'), to_unit=Unit('C'))  # from_unit doesn't exist
        with raises(ValueError):
            cup.convert(42, Unit('fake'), to_unit=Unit('bogus'))  # neither unit exists

    def test_convert_to_ref(self):
        cup = CustomUnitPolicy([
            ScaleUnitConversion(Unit('km'), Unit('m'), 1000),
            ScaleUnitConversion(Unit('mm'), Unit('m'), 0.001),
            AffineUnitConversion(Unit('C'), Unit('K'), 1, 273.15)])
        assert cup.convert_to_ref(42, Unit('km')) == 42000  # source to ref
        assert cup.convert_to_ref(42, Unit('m')) == 42  # ref to ref
        with raises(ValueError):
            cup.convert_to_ref(42, Unit('bogus'))  # unit doesn't exist

    def test_can_convert(self):
        cup = CustomUnitPolicy([
            ScaleUnitConversion(Unit('km'), Unit('m'), 1000),
            ScaleUnitConversion(Unit('mm'), Unit('m'), 0.001),
            AffineUnitConversion(Unit('C'), Unit('K'), 1, 273.15)])
        assert cup.can_convert(from_unit=Unit('km'), to_unit=Unit('m'))
        assert cup.can_convert(from_unit=Unit('m'), to_unit=Unit('km'))
        assert cup.can_convert(from_unit=Unit('km'), to_unit=Unit('mm'))
        assert not cup.can_convert(from_unit=Unit('km'), to_unit=Unit('C'))  # Don't share same ref unit
        assert not cup.can_convert(from_unit=Unit('bogus'), to_unit=Unit('m'))  # from_unit doesn't exist

    def test_ref_unit(self):
        cup = CustomUnitPolicy([ScaleUnitConversion(Unit('km'), Unit('m'), 1000)])
        assert cup.ref_unit(Unit('km')) == Unit('m')
        assert cup.ref_unit(Unit('m')) == Unit('m')
        with raises(ValueError):
            cup.ref_unit(Unit('furlong'))  # unit doesn't exist
