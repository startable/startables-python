"""
A scheme/algebraic expression parser/evaluator system aimed at parameter-expansion (templating)


## Background

The key usecase for this module is to allow interdependent inputs to be defined out of order, so that we could have a definition section

```
    'zRef': '(* 2 Lbase)'
    'zFoo': 'zRef + 7.3'
    'zBar': 'zRef + 0.2 Lbase'
```

and a set of inputs refering to the definitions via double-curly expansion, e.g. `{{zBar}}`, `{{(* 2 Lbase)}}`, `{{zBar + 3}}`, all of which are only evaluated after we specify a value for the input parametes (here: `Lbase`).


## Implementation plan

Because we expect a relatively low fraction of input tables to be parametrized, 
we have chosen a solution where each parameterized table has a reference to an environment
that notifies the table when it has been modified in place.
When the table is accessed, it can then recompute stale values.


## Sources
Scheme implementation is heavily inspired by [lisp.py](http://norvig.com/lispy.html) 
by Peter Norvig, and [extensions](https://github.com/adamhaney/lispy) by Adam Haney

Algebraic parser inspired by
https://codereview.stackexchange.com/a/160588
https://www.engr.mun.ca/~theo/Misc/exp_parsing.htm


(C) 2018 Orsted/Janus Wesenberg
"""
from pyscheme.special_forms import make_root_environment
from pyscheme.parse import parse_expression
from pyscheme.core import Environment
from pyscheme.typing import Expression
