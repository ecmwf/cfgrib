
import os.path

from eccodes_grib import dataset

TEST_DATA = os.path.join(os.path.dirname(__file__), 'sample-data', 'ERA5_levels.grib')


def test_Variable():
    dataset.Variable()


def test_Dataset():
    dataset.Dataset(TEST_DATA)
