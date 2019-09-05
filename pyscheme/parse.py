from pyscheme import parse_scheme
from pyscheme import parse_algebra
import re


def parse_expression(s: str):
    """
    Parse s as either a scheme or an algebraic expression

    If expression is of the form (...), it is assumed to be scheme.
    Note that this implies that some expressions that are clearly not
    scheme (e.g. "(a+3)*(b+5)" will be assumed scheme. Please work around
    this with unary plus or similar.
    """

    if re.match('\(.*\)$', s, re.MULTILINE):
        return parse_scheme.parse_expression(s)
    else:
        return parse_algebra.parse_expression(s)
