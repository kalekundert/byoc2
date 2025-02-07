import sys

from typing import Union, Optional
from numbers import Real
from tidyexc import Error

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


