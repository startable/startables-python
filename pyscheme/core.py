import weakref
from typing import Optional, Tuple, Set, Iterable, Dict

from pyscheme.typing import *


class Environment:
    """
    An environment is a 
    - parent environment
    - a map from symbols to symbol definitions

    Normally, an environment would store symbol values, i.e. the evaluated form 
    of the symbol definitions, but this would not support the main use-case of 
    a hierarchical set of parameter definitions that can be modified by 
    changing the root definitions.

    The environment object will notify observers when symbols definitions have changed.
    The notification will contain the fully expanded list of affected symbols, or None
    to indicate that all symbols should be considered unsafe.
    This design allows the environment to safely maintain a cache of pre-evaluated symbols.

    The `set!` builtin will update the value of a symbol to conform to normal 
    scheme semantics.
    This implies that `set!` values will/may be deleted when parameter values 
    are changed, but the current use case calls for separate child environments
    for the actual evaluations, so this should not be a problem.
    """

    def __init__(self,
                 parent: Optional['Environment'] = None,
                 values: Iterable[Tuple[str, Expression]] = (),
                 definitions: Iterable[Tuple[str, Expression]] = ()):
        self.parent = parent
        self._definition_map: Dict[str, Expression] = {k: v for k, v in definitions}
        self._value_map: Dict[str, Expression] = {k: v for k, v in values}
        self._update_listeners = weakref.WeakSet()

        if parent is not None:
            parent.add_update_listener(self._handle_update)

    def add_update_listener(self, listener):
        self._update_listeners.add(listener)

    def _handle_update(self, modified_symbols: Optional[Set[str]] = None):
        # Future performance improvement would track dependency 
        # of each evaluated symbol (by evaluating in mock environment)
        # and carefully update expression map to match/
        # For now, delete full cache on each update
        self._value_map.clear()
        self._notify_listeners(None)

    def _notify_listeners(self, modified_symbols=None):
        for listener in self._update_listeners:
            listener(modified_symbols)

    def evaluate(self, expr: Expression):
        """
        Evaluate expression in a child environment
        """
        return evaluate(expr, Environment(parent=self))

    def __getitem__(self, s: str):
        if s in self._value_map:
            return self._value_map[s]
        if s in self._definition_map:
            # Compute value from definition in a throwaway child environment
            value = self.evaluate(self._definition_map[s])
        elif self.parent:
            value = self.parent[s]
        else:
            # self is the root environment
            raise KeyError(f'Symbol "{s}" not defined')

        # Store symbol value in local cache, even if provided by parent
        self._value_map[s] = value
        return value

    def __setitem__(self, s: str, expr: Expression):
        # Defined terms cannot be set
        if s in self._value_map and s not in self._definition_map:
            self._value_map[s] = expr
        elif self.parent:
            self.parent[s] = expr
        else:
            raise KeyError(f'Symbol "{s}" has not been defined')

    def __contains__(self, s: str):
        return (
                s in self._value_map
                or s in self._definition_map
                or (self.parent and s in self.parent))

    def add(self, s: str, expr: Expression):
        self._value_map[s] = expr

    def update(self, values: Iterable[Tuple[str, Expression]]):
        """Add or update values in env"""
        self._value_map.update(values)

    def define(self, s: str, expr: Expression):
        """Add or replace definition"""
        self._definition_map[s] = expr
        self._handle_update(set(s))
        return self


def is_symbol(x: Expression, s: str):
    return isinstance(x, atoms.Symbol) and x == s


class Procedure:
    """A user-defined Scheme procedure."""

    def __init__(self, parms, exp, env):
        self.parms, self.exp, self.env = parms, exp, env

    def __call__(self, *args):
        return evaluate(self.exp, Environment(parent=self.env, values=zip(self.parms, args)))


def evaluate(x: Expression, env: Environment) -> Expression:
    """
        Evaluate an expression in an environment.
        Handle the special forms, https://courses.cs.washington.edu/courses/cse341/04wi/lectures/12-scheme.html:
        - define
        - if
        - cond
        - lambda
        - quote
        - set!
    """

    if isinstance(x, atoms.Symbol):  # variable reference
        return env[x]
    elif not isinstance(x, list):  # constant literal
        return x
    elif is_symbol(x[0], 'quote'):  # quotation
        (_, exp) = x
        return exp
    elif is_symbol(x[0], 'if'):  # conditional
        (_, test, conseq, alt) = x
        exp = (conseq if evaluate(test, env) else alt)
        return evaluate(exp, env)
    elif is_symbol(x[0], 'define'):  # definition
        (_, var, exp) = x
        env.add(var, evaluate(exp, env))
    elif is_symbol(x[0], 'set!'):  # assignment
        (_, var, exp) = x
        env[var] = evaluate(exp, env)
    elif is_symbol(x[0], 'lambda'):  # procedure
        (_, parms, body) = x
        return Procedure(parms, body, env)
    else:  # procedure call
        proc = evaluate(x[0], env)
        args = [evaluate(arg, env) for arg in x[1:]]
        return proc(*args)
