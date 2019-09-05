"""
This module is an empty shell: only allows single symbol expressions.

Some inspiration for a full parser implementation in python: 

"""

import re
from collections import namedtuple
from enum import Enum

from pyscheme.typing import *
from pyscheme.atoms import atom, Symbol


def parse_expression(s: str) -> Expression:
    """
    Parse s as an algebraic expression
    """
    return parse(tokenize(s))

    # if re.match('[_a-zA-Z]\w*',s):
    #     # A single symbol
    #     return Symbol(s)
    # else:
    #     raise NotImplementedError(f'General algebraic parser not implemented, cannot parse "{s}"')


class TokenType(Enum):
    OP = 1  # Operator
    NUM = 2  # Number
    OPAREN = 3  # Open parenthesis
    CPAREN = 4  # Close parenthesis
    END = 5  # End of input


Token = namedtuple('Token', 'type value')

_TOKEN_RE = re.compile(r'''
    \s*(?:                      # Optional whitespace, followed by one of
    ([+*/^-])                   # Operator
    |((?:\w+))                  # Atom 
    |(\()                       # Open parenthesis
    |(\))                       # Close parenthesis
    |(.))                       # Any other character is an error
''', re.VERBOSE)


def tokenize(expr):
    """Generate the tokens in the string expr, followed by END."""
    for match in _TOKEN_RE.finditer(expr):
        op, num, oparen, cparen, error = match.groups()
        if op:
            yield Token(TokenType.OP, op)
        elif num:
            yield Token(TokenType.NUM, atom(num))
        elif oparen:
            yield Token(TokenType.OPAREN, oparen)
        elif cparen:
            yield Token(TokenType.CPAREN, cparen)
        else:
            raise SyntaxError("Unexpected character: {!r}".format(error))
    yield Token(TokenType.END, "end of input")


def parse(tokens):
    """Parse iterable of tokens and return aparse tree as a scheme expression."""
    tokens = iter(tokens)  # Ensure we have an iterator.
    token = next(tokens)  # The current token.

    def error(expected):
        # Current token failed to match, so raise syntax error.
        raise SyntaxError("Expected {} but found {!r}"
                          .format(expected, token.value))

    def match(type, values=None):
        # If the current token matches type and (optionally) value,
        # advance to the next token and return True. Otherwise leave
        # the current token in place and return False.
        nonlocal token
        if token.type == type and (values is None or token.value in values):
            token = next(tokens)
            return True
        else:
            return False

    def term():
        # Parse a term starting at the current token.
        # TODO: handle unary +/-
        t = token
        if match(TokenType.NUM):
            return t.value
        elif match(TokenType.OPAREN):
            tree = addition()
            if match(TokenType.CPAREN):
                return tree
            else:
                error("')'")
        else:
            error("term")

    def exponentiation():
        # Parse an exponentiation starting at the current token.
        left = term()
        t = token
        if match(TokenType.OP, '^'):
            return [Symbol(t.value), left, exponentiation()]
        else:
            return left

    def multiplication():
        # Parse a multiplication or division starting at the current token.
        left = exponentiation()
        t = token
        while match(TokenType.OP, '*/'):
            right = exponentiation()
            left = [Symbol(t.value), left, exponentiation()]
        return left

    def addition():
        # Parse an addition or subtraction starting at the current token.
        left = multiplication()
        t = token
        while match(TokenType.OP, '+-'):
            left = [Symbol(t.value), left, multiplication()]
        return left

    tree = addition()
    if token.type != TokenType.END:
        error("end of input")
    return tree
