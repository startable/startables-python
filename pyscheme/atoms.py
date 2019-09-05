# from pyscheme.typing import Expression


class Symbol(str):
    pass


def atom(token) -> 'Expression':
    """Numbers become numbers; every other token is a symbol."""
    try:
        return int(token)
    except ValueError:
        try:
            return float(token)
        except ValueError:
            return Symbol(token)
