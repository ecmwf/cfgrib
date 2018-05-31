
import os.path

from eccodes_grib import dataset

TEST_DATA = os.path.join(os.path.dirname(__file__), 'sample-data', 'ERA5_levels.grib')


def test_Variable():
    dataset.Variable('tas', 130)


def test_Dataset():
    res = dataset.Dataset(TEST_DATA)
    assert len(res.variables) == 3
