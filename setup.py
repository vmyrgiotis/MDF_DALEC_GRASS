import pathlib
from setuptools import setup, find_packages

HERE = pathlib.Path(__file__).parent

VERSION = '0.1.0'
PACKAGE_NAME = 'MDF_DALEC_GRASS'
AUTHOR = 'Vasilis Myrgiotis'
AUTHOR_EMAIL = 'v.myrgioti@ed.ac.uk'
URL = 'https://github.com/vmyrgiotis/MDF_DALEC_GRASS'

LICENSE = 'MIT'
DESCRIPTION = 'A Bayesian model-data fusion algorithm for simulating carbon dynamics in grassland ecosystems'
LONG_DESCRIPTION = (HERE / "README.md").read_text()
LONG_DESC_TYPE = "text/markdown"

INSTALL_REQUIRES = ["numpy", "pandas","spotpy","sklearn","sentinelhub", "shapely", "datetime", "glob", "subprocess", "geopandas", "cdsapi","mpi4py"]
PYTHON_REQUIRES = '>=3.8'

setup(name=PACKAGE_NAME,
	version=VERSION,
	description=DESCRIPTION,
	long_description=LONG_DESCRIPTION,
	long_description_content_type=LONG_DESC_TYPE,
	author=AUTHOR,
	license=LICENSE,
	author_email=AUTHOR_EMAIL,
	url=URL,
	install_requires=INSTALL_REQUIRES,
	packages=find_packages()
	)
