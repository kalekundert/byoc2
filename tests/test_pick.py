#!/usr/bin/env python3

import byoc
import parametrize_from_file as pff

from utils import with_py, with_byoc

@pff.parametrize(
        schema=[
            pff.cast(
                pick_func=with_byoc.eval,
                values_iter=lambda x: byoc.ValuesIter('<param>', with_py.eval(x)),
                expected=with_py.eval,
            ),
            pff.error_or('expected', globals=with_byoc),
        ],
)
def test_pick_functions(pick_func, values_iter, expected, error):
    with error:
        assert pick_func(values_iter) == expected['value']
        assert values_iter.meta == expected['meta']

