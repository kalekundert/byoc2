import sys
import smartcall

from numbers import Real
from tidyexc import Error
from smartcall import PosOnly, KwOnly
from more_itertools import value_chain
from pathlib import Path

from typing import Union, Optional, TypeVar, Any, Callable

T = TypeVar('T')

class CastFuncs:
    """
    A collection of user-specified cast functions.

    This class abstracts two aspects of handling the *cast* functions that 
    users can provide to both getters and parameters:

    1. The user can provide either a single callable or an iterable of 
       callables.  This class converts either input into a list.  This list can 
       also be modified after the fact (e.g. by `toggle_param`).

    2. If the cast function can accept certain optional keyword arguments, 
       those arguments will be provided, to give extra information about the 
       context in which the function is being called.
    """

    def __init__(self, func_or_funcs):
        self.funcs = [
                x for x in value_chain(func_or_funcs)
                if x is not None
        ]

    def __call__(self, value, *, app, meta):
        for f in self.funcs:
            value = smartcall.call(
                    f,
                    PosOnly(value, required=True),
                    KwOnly(app=app),
                    KwOnly(meta=meta),
            )

        return value

def relpath(
        path: Any,
        *,
        meta: T,
        root_from_meta: Callable[[T], Path]=\
                lambda meta: Path(meta.path).parent,
) -> Path:
    """
    Resolve paths loaded from a file.  Relative paths are interpreted as being 
    relative to the parent directory of the file they were loaded from.

    Arguments:
        value:
            The path to interpret relative to the directory specified by 
            *meta*.

        meta:

        root_from_meta:
            A callable that returns the parent directory for relative paths, 
            given a metadata object describing how the value in question was 
            loaded. The default implementation assumes that the metadata object 
            has a :attr:`location` attribute that specifies the path to the 
            relevant file.  This will work if (i) the value was actually loaded 
            from a file and (ii) the default pick function was used (i.e. 
            `first`).  For other pick functions, you may need to modify this 
            argument accordingly.

    Returns:
        An absolute path.
    """
    path = Path(path)
    if path.is_absolute():
        return path

    root = root_from_meta(meta)
    return root.resolve() / path

def arithmetic_eval(expr: Union[str, Real], vars: Optional[dict]=None) -> Real:
    """\
    Evaluate the given arithmetic expression.

    Arguments:
        expr:
            The expression to evaluate.  The syntax is identical to python, but 
            only `int` literals, `float` literals, binary operators (except 
            left/right shift, bitwise and/or/xor, and matrix multiplication),
            unary operators, and names provided by the *vars* dictionary are 
            allowed.  If this argument is already a numeric type, it will be 
            returned unchanged.

        vars:
            The variables to allow in the given expression.  The keys of this 
            dictionary give the names of the variables.  The values must be 
            integers or floats.

    Returns:
        The value of the given expression.

    Raises:
        SyntaxError: If *expr* cannot be parsed for any reason.
        TypeError: If the *expr* argument is not a string or a number.
        ZeroDivisionError: If *expr* divides by zero.

    It is safe to call this function on untrusted input, as there is no way to 
    construct an expression that will execute arbitrary code.
    """
    import ast, operator

    if vars is None:
        vars = {}
    for k, v in vars.items():
        if not isinstance(v, (int, float)):
            raise TypeError(f"variables must be int or float, but {k}={v!r}")

    if isinstance(expr, Real):
        return expr
    if not isinstance(expr, str):
        raise TypeError(f"expected str, not: {type(expr)}")

    operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.FloorDiv: operator.floordiv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow,

            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
    }

    def eval_node(node):
        if sys.version_info[:2] < (3, 8):
            if isinstance(node, ast.Num):
                return node.n
        else:
            if isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)):
                    return node.value
                else:
                    err = ArithmeticError(expr, non_number=node.value)
                    err.blame += "{non_number!r} is not a number"
                    raise err

        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            try:
                return vars[node.id]
            except KeyError:
                err = ArithmeticError(expr, var=node.id)
                err.blame += "name '{var}' is not defined"
                raise err from None

        if isinstance(node, ast.BinOp):
            try:
                op = operators[type(node.op)]
            except KeyError:
                err = ArithmeticError(expr, op=node.op)
                err.blame += "the {op.__class__.__name__} operator is not supported"
                raise err from None

            left = eval_node(node.left)
            right = eval_node(node.right)
            return op(left, right)

        if isinstance(node, ast.UnaryOp):
            assert type(node.op) in operators
            op = operators[type(node.op)]
            value = eval_node(node.operand)
            return op(value)

        raise ArithmeticError(expr)

    root = ast.parse(expr.lstrip(" \t"), mode='eval')
    return eval_node(root.body)

def int_eval(expr: Union[str, Real], vars: Optional[dict]=None) -> int:
    """\
    Same as `arithmetic_eval()`, but convert the result to `int`.
    """
    return int(arithmetic_eval(expr, vars))

def float_eval(expr: Union[str, Real], vars: Optional[dict]=None) -> float:
    """\
    Same as `arithmetic_eval()`, but convert the result to `float`.
    """
    return float(arithmetic_eval(expr, vars))

class ArithmeticError(Error, SyntaxError):

    def __init__(self, expr, **kwargs):
        super().__init__(expr=expr, **kwargs)
        self.brief = "unable to evaluate arithmetic expression"
        self.info += "expression: {expr}"


