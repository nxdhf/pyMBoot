#!/usr/bin/env python

# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

from os import path
from setuptools import setup, find_packages
from mboot import __version__, __license__, __author__, __contact__


def long_description():
    try:
        import pypandoc

        readme_path = path.join(path.dirname(__file__), 'README.md')
        return pypandoc.convert(readme_path, 'rst').replace('\r', '')
    except (IOError, ImportError):
        return (
            "More on: https://github.com/nxdhf/pyMBoot"
        )

test_requirements = [
    "pytest>=5.1.1",
    "pytest-console-scripts>=0.1.9",
    "pytest-cov>=2.7.1",
    "coveralls>=1.8.2",
],

setup(
    name='mboot',
    version=__version__,
    # license=__license__,
    # author=__author__,
    # author_email=__contact__,
    # url="https://github.com/nxdhf/pyMBoot",
    # description='Python module for communication with NXP MCU Bootloader',
    # long_description=long_description(),
    # keywords="NXP MCU Bootloader",
    platforms="Windows, Linux",
    python_requires=">=3.5",
    # tests_require = test_requirements,
    setup_requires=[
        'setuptools>=40.0',
        # 'pytest-runner'
    ],
    install_requires=[
        'pyserial==3.4',
        'bincopy==16.0.0',
        'easy_enum==0.2.0',
        'pyusb==1.0.0;platform_system!="Windows"',
        'pywinusb==0.4.2;platform_system=="Windows"',
        'pyftdi==0.29.4'
    ],
    extras_require={
        'test': test_requirements,
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Environment :: Console',
        'License :: OSI Approved :: BSD License',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development :: Embedded Systems',
        'Topic :: Utilities',
    ],
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'mboot = mboot.__main__:main',
        ],
    }
)
