
import os.path

from eccodes_grib import dataset
from eccodes_grib import messages

TEST_DATA = os.path.join(os.path.dirname(__file__), 'sample-data', 'ERA5_one-variable_levels.grib')


def test_IndexedVariable():
    index = messages.Index(path=TEST_DATA, index_keys=['paramId'])
    dataset.IndexedVariable(name='tas', paramId=130, index=index)


def test_Dataset():
    res = dataset.Dataset(TEST_DATA)
    assert len(res.variables) == 1
