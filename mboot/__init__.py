# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

from .enums import CommandTag, PropertyTag, StatusCode
from .memorytool import MemoryBlock, Memory, Flash
from .peripheral import parse_peripheral, scan_usb, scan_uart, scan_spi, scan_i2c
from .mboot import McuBoot, decode_property_value, is_command_available
from .decorator import global_error_handler
from .exception import McuBootGenericError, McuBootCommandError, McuBootDataError, McuBootConnectionError, McuBootTimeOutError
from .cli import main

__author__ = "Martin Olejar"
__contact__ = "martin.olejar@gmail.com"
__version__ = '0.2.0'
__license__ = "BSD3"
__status__ = 'Development'

__all__ = [
    # global methods
    'decode_property_value',
    'is_command_available',
    # memory tool
    'MemoryBlock',
    'Memory',
    'Flash',
    # peripheral
    'parse_peripheral',
    'scan_usb',
    'scan_uart',
    'scan_spi',
    # classes
    'McuBoot',
    # enums
    'CommandTag',
    'PropertyTag',
    'StatusCode',
    # decorator
    'global_error_handler',
    # exceptions
    'McuBootGenericError',
    'McuBootCommandError',
    'McuBootDataError',
    'McuBootConnectionError',
    'McuBootTimeOutError'
]
