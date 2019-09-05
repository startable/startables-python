import typing
import numbers
from pyscheme import atoms

Number = typing.NewType('Number', numbers.Complex)
Expression = typing.Union[Number, atoms.Symbol, typing.List['Expression']]