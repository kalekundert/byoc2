import byoc
import parametrize_from_file as pff

with_py = pff.Namespace()

@pff.parametrize(schema=with_py.eval)
def test_lookup(x, key, expected):
    assert byoc.lookup(x, key) == expected


