import byoc
import parametrize_from_file as pff

from utils import with_py

@pff.parametrize(
        schema=[
            pff.cast(expr=with_py.eval, vars=with_py.eval, expected=with_py.eval),
            pff.defaults(vars=None),
            pff.error_or('expected'),
        ],
)
def test_arithmetic_eval(expr, vars, expected, error):
    with error:
        assert byoc.arithmetic_eval(expr, vars) == expected

    with error:
        assert byoc.int_eval(expr, vars) == int(expected)

    with error:
        assert byoc.float_eval(expr, vars) == float(expected)

