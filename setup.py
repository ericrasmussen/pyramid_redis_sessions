__version__ = '0.9b'

import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.rst')).read()

testing_extras = ['pkginfo', 'nose', 'coverage']

setup(name='pyramid_redis_sessions',
      version=__version__,
      description='Pyramid web framework session factory backed by Redis',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        'Intended Audience :: Developers',
        "Framework :: Pylons",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        ],
      keywords='pyramid session cache redis',
      author='Eric Rasmussen',
      author_email='eric@chromaticleaves.com',
      url='https://github.com/ericrasmussen/pyramid_redis_sessions',
      license='FreeBSD',
      packages=find_packages(),
      test_suite='pyramid_redis_sessions.tests',
      include_package_data=True,
      zip_safe=False,
      tests_require=['pkginfo', 'nose'],
      install_requires=[
        'redis>=2.4.11',
        'pyramid>=1.3',
        ],
      entry_points='',
      extras_require = {
          'testing':testing_extras,
          },
)
