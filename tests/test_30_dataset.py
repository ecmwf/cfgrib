
import os.path

from eccodes_grib import dataset

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-members-one_var.grib')


def test_Dataset():
    dataset.Dataset(TEST_DATA)


def test_Variable():
    ds = dataset.Dataset(TEST_DATA)
    res = dataset.Variable(name='tas', paramId=130, stream=ds.stream)
    assert res.name == 'tas'
