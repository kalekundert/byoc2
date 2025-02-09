import byoc
import parametrize_from_file as pff

from utils import with_py

@pff.parametrize(
        schema=pff.cast(
            collection=with_py.eval,
            expected=with_py.eval,
        ),
)
def test_meta_from_collection(collection, expected):
    assert byoc.meta_from_collection(collection) == expected
