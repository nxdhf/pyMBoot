# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

import sys
import time
import logging
import struct

# relative imports
from .enums import CommandTag, PropertyTag, StatusCode
from .constant import Interface, KeyOperation
from .misc import atos, size_fmt
from .tool import read_file, write_file, check_key
# from .protocol import UartProtocol, UsbProtocol, FPType
from .exception import McuBootGenericError, McuBootCommandError
from .uart import UART
from .usb import RawHID
from .spi import SPI
from .memorytool import MemoryBlock, Memory, Flash
from .peripheral import parse_port

########################################################################################################################
# Helper functions
########################################################################################################################

def decode_property_value(property_tag, raw_value, memory_id=None, last_cmd_response=None):
    if property_tag == PropertyTag.CURRENT_VERSION:
        str_value = "{0:d}.{1:d}.{2:d}".format((raw_value >> 16) & 0xFF, (raw_value >> 8) & 0xFF, raw_value & 0xFF)

    elif property_tag == PropertyTag.AVAILABLE_PERIPHERALS:
        str_value = []
        for key, value in McuBoot.INTERFACES.items():
            if value[0] & raw_value:
                str_value.append(key)

    elif property_tag == PropertyTag.FLASH_SECURITY_STATE:
        str_value = 'Unlocked' if raw_value == 0 else 'Locked'

    elif property_tag == PropertyTag.AVAILABLE_COMMANDS:
        str_value = []
        for name, value, desc in CommandTag:
            if (1 << value) & raw_value:
                str_value.append(name)

    elif property_tag in (PropertyTag.MAX_PACKET_SIZE, PropertyTag.FLASH_SECTOR_SIZE,
                          PropertyTag.FLASH_SIZE, PropertyTag.RAM_SIZE):
        str_value = size_fmt(raw_value)

    elif property_tag in (PropertyTag.RAM_START_ADDRESS, PropertyTag.FLASH_START_ADDRESS,
                          PropertyTag.SYSTEM_DEVICE_IDENT):
        str_value = '0x{:08X}'.format(raw_value)
    
    elif property_tag == PropertyTag.EXTERNAL_MEMORY_ATTRIBUTES and memory_id:
        # start_address, total_size, _, _, block_size
        result = struct.unpack_from('<5L', last_cmd_response, 12) # upack(<'4B7L',last_cmd_response)
        start_address, total_size, _, _, block_size = result
        str_value = ''' External Memory Attributes:
                    Memory Id: 0x{:X}
                    Start Address: 0x{:08X}
                    Total Size: 0x{:08X} KB = {:5.3f} GB
                    Block Size: 0x{:X} Bytes'''.format(memory_id, result[0], result[1], result[1]/1024/1024, result[4])
    else:
        str_value = '{:d}'.format(raw_value)

    return str_value


def is_command_available(command_tag, property_raw_value):
    return True if (1 << command_tag) & property_raw_value else False

########################################################################################################################
# MCUBoot interfaces
########################################################################################################################

# DEVICES = {
#     # NAME   | VID   | PID
#     'MKL27': (0x15A2, 0x0073),
#     'LPC55': (0x1FC9, 0x0021),
#     'K82F' : (0x15A2, 0x0073),
#     '232h' : (0x403,0x6014)
# }


# def scan_usb(device_name=None):
#     """ MCUBoot: Scan commected USB devices
#     :rtype : list
#     """
#     devices = []

#     if device_name is None:
#         for name, value in DEVICES.items():
#             devices += RawHID.enumerate(value[0], value[1])
#     else:
#         if ':' in device_name:
#             vid, pid = device_name.split(':')
#             devices = RawHID.enumerate(int(vid, 0), int(pid, 0))
#         else:
#             if device_name in DEVICES:
#                 vid = DEVICES[device_name][0]
#                 pid = DEVICES[device_name][1]
#                 devices = RawHID.enumerate(vid, pid)
#     return devices


# def scan_uart():
#     raise NotImplemented("Function is not implemented")

# def scan_uart():
#     raise NotImplemented("Function is not implemented")


########################################################################################################################
# McuBoot Class
########################################################################################################################

class McuBoot(object):

    INTERFACES = {
        #  MCUBoot Interface | mask | default speed
        'UART':      [0x00000001, 115200],
        'I2C-Slave': [0x00000002, 400],
        'SPI-Slave': [0x00000004, 400],
        'CAN':       [0x00000008, 500],
        'USB-HID':   [0x00000010, 12000000],
        'USB-CDC':   [0x00000020, 12000000],
        'USB-DFU':   [0x00000040, 12000000],
    }

    def __init__(self):
        self.cli_mode = False
        self._itf_ = None
        self.current_interface = None
        self.reopen_args = None
        self.timeout = None or 5000
        self._usb_dev = None
        self._uart_dev = None
        self._spi_dev = None
        self._pg_func = None
        self._pg_start = 0
        self._pg_end = 100
        self._abort = False

    # @staticmethod
    # def _parse_status(data):
    #     return unpack_from('<I', data, 4)[0]

    # @staticmethod
    # def _parse_value(data):
    #     return unpack_from('<I', data, 8)[0]

    def set_handler(self, progressbar, start_val=0, end_val=100):
        self._pg_func = progressbar
        self._pg_start = start_val
        self._pg_end = end_val

    def abort(self):
        self._abort = True

    def is_open(self):
        """ MCUBoot: Check if device connected
        """
        if self._usb_dev is not None:
            return True
        else:
            return False

    def open_usb(self, vid_pid):
        """ MCUBoot: Connect by USB
        """
        if isinstance(vid_pid, str):
            _vid_pid = parse_port(Interface.USB.name, vid_pid)
        else:   # Default input tuple in cli mode, no conversion required
            _vid_pid = vid_pid
        dev = RawHID.enumerate(*_vid_pid)[0]
        if dev is not None:
            logging.info('Connect: %s', dev.info())
            self._itf_ = dev    # Already open, simple assignment
            self._itf_.open()
            self.current_interface = Interface.USB
            self.reopen_args = vid_pid
            return True
        else:
            info = 'Can not find vid,pid: 0x{p[0]:04X}, {p[1]:04X}'.format(p=_vid_pid)
            if self.cli_mode:   # Fast failure in cli mode
                raise McuBootGenericError(info)
            logging.info(info)
            return False

    def open_uart(self, port, baudrate):
        """ MCUBoot: Connect by UART
        """
        if self.cli_mode:   # checked in cli mode
            _port = port
        else:
            _port = parse_port(Interface.UART.name, port)
        try:
            self._itf_ = UART()
            self._itf_.open(_port, baudrate)
        except Exception:
            logging.info('Open UART failed, UART disconnected !')
            if self.cli_mode:   # Fast failure in cli mode
                raise
            return False
        else:
            self.current_interface = Interface.UART
            self.reopen_args = (port, baudrate)
            return True
        # else:
        #     logging.info('UART Disconnected !')
        #     return False
    
    def open_spi(self, vid_pid, freq, mode):
        """ MCUBoot: Connect by UART
        """
        if isinstance(vid_pid, str):
            _vid_pid = parse_port(Interface.SPI.name, vid_pid)
        else:   # Default input tuple in cli mode, no conversion required
            _vid_pid = vid_pid
        try:
            self._itf_ = SPI(freq, mode)
            self._itf_.open(*_vid_pid)
        except Exception:
            logging.info('Open SPI failed, SPI disconnected !')
            if self.cli_mode:   # Fast failure in cli mode
                raise
            return False
        else:
            self.current_interface = Interface.SPI
            self.reopen_args = (_vid_pid, freq, mode)
            return True

    def close(self):
        """ MCUBoot: Disconnect device
        """
        if self._usb_dev:
            self._usb_dev.close()
            self._usb_dev = None
        elif self._uart_dev:
            self._uart_dev.close()
            self._uart_dev = None
        else:
            return
    
    def get_memory_range(self):
        mstart = self.get_property(PropertyTag.RAM_START_ADDRESS)
        mlength = self.get_property(PropertyTag.RAM_SIZE)
        self.memory = Memory(mstart, None, mlength)
        # No on-chip flash situation
        fstart = self.get_property(PropertyTag.FLASH_START_ADDRESS)
        flength = self.get_property(PropertyTag.FLASH_SIZE)
        self.flash = Flash(fstart, None, flength)

    def is_in_memory(self, block):
        return block in self.memory

    def is_in_flash(self, block):
        return block in self.flash

    def get_mcu_info(self):
        """ MCUBoot: Get MCU info (available properties collection)
        :return List of {dict}
        """
        mcu_info = {}
        if self._itf_ is None:
            logging.info('Disconnected !')
            return None

        for property_name, property_tag, _ in PropertyTag:
            try:
                raw_value = self.get_property(property_tag)
                str_value = decode_property_value(property_tag, raw_value)
            except McuBootCommandError:
                continue
            mcu_info.update({property_name: str_value})

        return mcu_info

    def get_exmemory_info(self, memory_id):
        try:
            raw_value = self.get_property(PropertyTag.EXTERNAL_MEMORY_ATTRIBUTES, memory_id)
            str_value = decode_property_value(PropertyTag.EXTERNAL_MEMORY_ATTRIBUTES, raw_value, memory_id, self._itf_.last_cmd_response)
        except McuBootCommandError:
            pass
        str_list = [' ' + value.strip() for value in str_value.split('\n')]
        str_value = '\n '.join(str_list)
        return str_value

    def flash_erase_all(self, memory_id = 0):
        """ MCUBoot: Erase complete flash memory without recovering flash security section
        CommandTag: 0x01
        :param memory_id: External memory id
        """
        logging.info('TX-CMD: FlashEraseAll [ memoryId = 0x%X ]', memory_id)
        # Prepare FlashEraseAll command
        cmd = struct.pack('4BI', CommandTag.FLASH_ERASE_ALL, 0x00, 0x00, 0x00, memory_id)
        # Process FlashEraseAll command
        self._itf_.write_cmd(cmd)

    def flash_erase_region(self, start_address, length, memory_id = 0):
        """ MCUBoot: Erase specified range of flash
        CommandTag: 0x02
        :param start_address: Start address
        :param length: Count of bytes
        :param memory_id: External memory id
        """
        logging.info('TX-CMD: FlashEraseRegion [ StartAddr=0x%08X | len=0x%X | memoryId = 0x%X ]', start_address, length, memory_id)
        # Prepare FlashEraseRegion command
        cmd = struct.pack('<4B3I', CommandTag.FLASH_ERASE_REGION, 0x00, 0x00, 0x02, start_address, length, memory_id)
        # Process FlashEraseRegion command
        self._itf_.write_cmd(cmd, self.timeout)

    def read_memory(self, start_address, length, filename = None, memory_id = 0):
        """ MCUBoot: Read data from MCU memory
        CommandTag: 0x03
        :param start_address: Start address
        :param length: Count of bytes
        :param filename: The file to be read
        :param memory_id: External memory id
        :return List of bytes
        """
        if length == 0:
            raise ValueError('Data len is zero')
        if isinstance(filename, int):
            memory_id = filename
            filename = None

        logging.info('TX-CMD: ReadMemory [ StartAddr=0x%08X | len=0x%X | memoryId = 0x%X ]', start_address, length, memory_id)
        # Prepare ReadMemory command
        cmd = struct.pack('<4B3I', CommandTag.READ_MEMORY, 0x00, 0x00, 0x03, start_address, length, memory_id)
        # Process ReadMemory command
        self._itf_.write_cmd(cmd)
        # Process Read Data
        data = self._itf_.read_data(length)
        if filename:
            write_file(filename, data)
            logging.info("Successfully saved into: {}".format(filename))
        return data

    def write_memory(self, start_address, filename, memory_id = 0):
        """ MCUBoot: Write data into MCU memory
        CommandTag: 0x04
        :param start_address: Start address
        :param data: List of bytes
        :param filename: The file to be written
        :param memory_id: External memory id
        :return Count of wrote bytes
        """
        if isinstance(filename, str):   # Enter the file name
            data, address = read_file(filename, start_address)
        else:   # Enter the file data
            address = start_address
            data = filename
        if len(data) == 0:
            raise ValueError('Data len is zero')
        logging.info('TX-CMD: WriteMemory [ StartAddr=0x%08X | len=0x%x | memoryId = 0x%X ]', address, len(data), memory_id)
        # Prepare WriteMemory command
        cmd = struct.pack('<4B3I', CommandTag.WRITE_MEMORY, 0x00, 0x00, 0x03, address, len(data), memory_id)
        # get max packet size
        max_packet_size = self.get_property(PropertyTag.MAX_PACKET_SIZE, memory_id)
        # Process WriteMemory command
        self._itf_.write_cmd(cmd)
        # Process Write Data
        return self._itf_.write_data(data, max_packet_size)

    def fill_memory(self, start_address, length, pattern=0xFFFFFFFF, unit='word'):
        """ MCUBoot: Fill MCU memory with specified pattern
        CommandTag: 0x05
        :param start_address: Start address (must be word aligned)
        :param length: Total length of padding, count of bytes
        :param pattern: The pattern used for padding that must match the unit and its length cannot exceed one word
        :param unit: Process pattern according to word, short(half-word), byte
        """
        try:
            if unit == 'word':
                _pattern = pattern
            elif unit == 'short':
                word = struct.pack('<2H', pattern, pattern)
                _pattern = struct.unpack('<I', word)[0]
            elif unit == 'byte':
                word = struct.pack('<4B', pattern, pattern, pattern, pattern)
                _pattern = struct.unpack('<I', word)[0]
            else:
                raise McuBootGenericError('Have no unit {}'.format(unit))
        except struct.error as e:
            raise McuBootGenericError('Pattern 0x{:08X} does not match unit {}'.format(pattern, unit))

        logging.info('TX-CMD: FillMemory [ address=0x%08X | len=0x%X | patern=0x%08X | unit=%s ]', 
            start_address, length, pattern, unit)
        # Prepare FillMemory command
        cmd = struct.pack('<4B3I', CommandTag.FILL_MEMORY, 0x00, 0x00, 0x03, start_address, length, _pattern)
        # Process FillMemory command
        self._itf_.write_cmd(cmd)

    def flash_security_disable(self, backdoor_key):
        """ MCUBoot: Disable flash security by backdoor key
        CommandTag: 0x06
        :param backdoor_key: back door key string, such as "ASCII = S:123...8" or "HEX = X:010203...08"
        """
        if isinstance(backdoor_key, str):
            key = check_key(backdoor_key)
        logging.info('TX-CMD: FlashSecurityDisable [ backdoor_key [0x] = %s ]', atos(key))
        # Prepare FlashSecurityDisable command
        cmd = struct.pack('4B', CommandTag.FLASH_SECURITY_DISABLE, 0x00, 0x00, 0x02)
        cmd += bytes(key[3::-1])
        cmd += bytes(key[:3:-1])
        # Process FlashSecurityDisable command
        self._itf_.write_cmd(cmd)

    def get_property(self, prop_tag, memory_id = 0):
        """ MCUBoot: Get value of specified property
        CommandTag: 0x07
        :param prop_tag: The property ID (see Property enumerator)
        :param memory_id: External memory id
        :return {dict} with 'RAW' and 'STRING/LIST' value
        """
        logging.info('TX-CMD: GetProperty->%s [ PropertyTag: %d | memoryId = 0x%X ]', 
            PropertyTag[prop_tag], PropertyTag[PropertyTag[prop_tag]], memory_id)
        # Prepare GetProperty command
        # if memory_id is None:
        #     memory_id = 0
        #     cmd = struct.pack('<4BI', CommandTag.GET_PROPERTY, 0x00, 0x00, 0x01, prop_tag)
        # else:
        #     cmd = struct.pack('<4B2I', CommandTag.GET_PROPERTY, 0x00, 0x00, 0x02, prop_tag, memoryId)
        cmd = struct.pack('<4B2I', CommandTag.GET_PROPERTY, 0x00, 0x00, 0x02, prop_tag, memory_id)
        # Process FillMemory command
        raw_value = self._itf_.write_cmd(cmd)

        logging.info('RX-CMD: %s = %s', PropertyTag[prop_tag], decode_property_value(prop_tag, 
            raw_value, memory_id, self._itf_.last_cmd_response))
        return raw_value

    def set_property(self, prop_tag, value, memory_id = 0):
        """ MCUBoot: Set value of specified property
        CommandTag: 0x0C
        :param  property_tag: The property ID (see Property enumerator)
        :param  value: The value of selected property
        :param memory_id: External memory id
        """
        logging.info('TX-CMD: SetProperty->%s = %d [ memoryId = 0x%X ]', PropertyTag[prop_tag], value, memory_id)
        # Prepare SetProperty command
        cmd = struct.pack('<4B3I', CommandTag.SET_PROPERTY, 0x00, 0x00, 0x02, prop_tag, value, memory_id)
        # Process SetProperty command
        self._itf_.write_cmd(cmd)

    def receive_sb_file(self, filename):
        """ MCUBoot: Receive SB file
        CommandTag: 0x08
        :param filename: SB file name or data
        """
        if isinstance(filename, str):
            with open(filename, 'rb') as f:
                data = f.read()
        if len(data) == 0:
            raise ValueError('Data len is zero')
        logging.info('TX-CMD: Receive SB file [ len=%d ]', len(data))
        # Prepare WriteMemory command
        cmd = struct.pack('<4BI', CommandTag.RECEIVE_SB_FILE, 0x01, 0x00, 0x01, len(data))
        # get max packet size
        max_packet_size = self.get_property(PropertyTag.MAX_PACKET_SIZE)
        # Process WriteMemory command
        self._itf_.write_cmd(cmd)
        # Process Write Data
        return self._itf_.write_data(data, max_packet_size)

    def execute(self, jump_address, argument, sp_address):
        """ MCUBoot: Fill MCU memory with specified pattern
        CommandTag: 0x09
        :param jump_address: Jump address (must be word aligned)
        :param argument: Function arguments address
        :param sp_address: Stack pointer address
        """
        logging.info('TX-CMD: Execute [ JumpAddr=0x%08X | ARG=0x%08X  | SP=0x%08X ]', jump_address, argument,
                     sp_address)
        # Prepare Execute command
        cmd = struct.pack('<4B3I', CommandTag.EXECUTE, 0x00, 0x00, 0x03, jump_address, argument, sp_address)
        # Process Execute command
        self._itf_.write_cmd(cmd)

    def call(self, call_address, argument):
        """ MCUBoot: Fill MCU memory with specified pattern
        CommandTag: 0x0A
        :param call_address: Call address (must be word aligned)
        :param argument: Function arguments address
        """
        logging.info('TX-CMD: Call [ CallAddr=0x%08X | ARG=0x%08X]', call_address, argument)
        # Prepare Call command
        cmd = struct.pack('<4B2I', CommandTag.CALL, 0x00, 0x00, 0x02, call_address, argument)
        # Process Call command
        self._itf_.write_cmd(cmd)

    def reset(self):
        """ MCUBoot: Reset MCU
        CommandTag: 0x0B
        """
        logging.info('TX-CMD: Reset MCU')
        # Prepare Reset command
        cmd = struct.pack('4B', CommandTag.RESET, 0x00, 0x00, 0x00)
        # Process Reset command
        try:
            self._itf_.write_cmd(cmd)
        except:
            pass
        # else:
        #     if hasattr(self._itf_, 'set_handler'):
        #         self._itf_.set_handler(None)
        #         self._itf_.close()
                
        #         self._itf_.open()
        if self.cli_mode == False:
            '''
            SPI-1M:     0.005s
            uart-57600: 0.01s
            uart-115200:0.009s
            '''
            if self.current_interface == Interface.USB:
                self.close()
                time.sleep(0.4)
                self.open_usb(self.reopen_args)
            elif self.current_interface == Interface.UART:
                time.sleep(0.01)    # Wait 10 ms for the device to complete reset
            elif self.current_interface == Interface.SPI:
                time.sleep(0.005)   # Wait 5 ms for the device to complete reset

    def flash_erase_all_unsecure(self):
        """ MCUBoot: Erase complete flash memory and recover flash security section
        CommandTag: 0x0D
        """
        logging.info('TX-CMD: FlashEraseAllUnsecure')
        # Prepare FlashEraseAllUnsecure command
        cmd = struct.pack('4B', CommandTag.FLASH_ERASE_ALL_UNSECURE, 0x00, 0x00, 0x00)
        # Process FlashEraseAllUnsecure command
        self._itf_.write_cmd(cmd)

    def flash_read_once(self, index, byte_count):
        """ MCUBoot: Read from MCU flash program once region (max 8 bytes)
        CommandTag: 0x0F
        :param index: Start index
        :param byte_count: Count of bytes, Must be 4-byte aligned.
        :return The value read from the IRF
        """
        if byte_count == 4:
            s_format = '<I'
            s_info = 'Response word: 0x{0:08X} ({0})'
        elif byte_count == 8:
            s_format = '<Q'
            s_info = 'Response word: 0x{0:016X} ({0})'
        else:
            raise McuBootGenericError('invalid byte_count arguments: {}'.format(byte_count))
        logging.info('TX-CMD: FlashReadOnce [ Index=%d | len=%d ]', index, byte_count)
        # Prepare FlashReadOnce command
        cmd = struct.pack('<4B2I', CommandTag.FLASH_READ_ONCE, 0x00, 0x00, 0x02, index, byte_count)
        # Process FlashReadOnce command
        self._itf_.write_cmd(cmd)
        # Process Response
        payload = self._itf_.last_cmd_response
        word = struct.unpack_from(s_format, payload, 12)[0]
        logging.info(s_info.format(word))
        return word
        # response_word_len = struct.unpack_from('<B', self._itf_.last_cmd_response,3)[0]
        # value_word_len = response_word_len -2
        # index = 12
        # while value_word_len:
        #     word = struct.unpack_from('<I', self._itf_.last_cmd_response, 12)[0]
        #     logging.info('Response word: 0x{0:08X} ({0})'.format(word))
        #     index += 4
        #     value_word_len -= 1

    def efuse_read_once(self, index):
        """Read one word of OCOTP Field, 'efuse_read_once' is alias of 'flash_read_once'
        :param index: Start index
        """
        return self.flash_read_once(index, 4)

    def flash_program_once(self, index, byte_count, data):
        """ MCUBoot: Write into MCU flash program once region (max 8 bytes)
        CommandTag: 0x0E
        :param index: Start index
        :byte_count: Count of bytes, Must be 4-byte aligned.
        :param data: List of bytes or int
        """
        if isinstance(data, int):
            # Detecting parameter correctness
            data_len = len(hex(data)[2:])
            if data_len <= 8:
                byte_len = 4
                if byte_len != byte_count:
                    raise McuBootGenericError('byte_count do not match data!')
                # s_format = '<I'
            elif data_len <= 16:
                byte_len = 8
                if byte_len != byte_count:
                    raise McuBootGenericError('byte_count do not match data!')
            else:
                raise McuBootGenericError('invalid data byte_count arguments: 0x{:X}'.format(data))
            # Int convert to bytes
            data_bytes = (data).to_bytes(byte_count, byteorder='little')
        else:
            # Detecting parameter correctness
            data_len = len(data)
            if data_len == 4:
                if byte_len != byte_count:
                    raise McuBootGenericError('byte_count do not match data!')
            elif data_len == 8:
                if byte_len != byte_count:
                    raise McuBootGenericError('byte_count do not match data!')
            else:
                raise McuBootGenericError('invalid data byte_count arguments: 0x{0:X} ({0})'.format(int.from_bytes(data, byteorder='little')))
            # Named alias
            data_bytes = data
        # length = len(data)
        # if (index + length) > 8:
        #     length = 8 - index
        # if length == 0:
        #     raise ValueError('Index out of range')
        logging.info('TX-CMD: FlashProgramOnce [ Index=%d | Data[0x]: %s ]', index, atos(data_bytes[:byte_count]))
        # Prepare FlashProgramOnce command
        cmd = struct.pack('<4B2I', CommandTag.FLASH_PROGRAM_ONCE, 0x00, 0x00, 0x03, index, byte_count)
        cmd += bytes(data_bytes)
        # Process FlashProgramOnce command
        self._itf_.write_cmd(cmd)
        return length

    def efuse_program_once(self, index, data):
        """ MCUBoot: Write into MCU flash program once region (max 8 bytes), 'efuse-program-once' is alias of 'flash-program-once'
        :param index: Start index
        :param data: List of bytes or int
        """
        self.flash_program_once(index, 4, data)

    def flash_read_resource(self, start_address, byte_count, option=1, filename=None):
        """ MCUBoot: Reads the contents of Flash IFR or Flash Firmware ID as specified 
        by 'option' and writes result to file or stdout if 'filename' is not specified.
        CommandTag: 0x10
        :param start_address: start address
        :param byte_count: Count of bytes, Must be 4-byte aligned.
        :param option: Indicates which area to be read. 0 means Flash IFR, 1 means Flash Firmware ID.
        :return resource data bytes
        """
        logging.info('TX-CMD: FlashReadResource [ StartAddr=0x%08X | len=%d ]', start_address, byte_count)
        # Prepare FlashReadResource command
        cmd = struct.pack('<4B3I', CommandTag.FLASH_READ_RESOURCE, 0x00, 0x00, 0x03, start_address, byte_count, option)
        # Process FlashReadResource command
        raw_value = self._itf_.write_cmd(cmd)
        rx_len = raw_value
        length = min(byte_count, rx_len)
        # Process Read Data
        data = self._itf_.read_data(length)
        if filename:
            write_file(filename, data)
            logging.info("Successfully saved into: {}".format(filename))
        return data

    def configure_memory(self, memory_id, address):
        '''MCUBoot: Configure external memory
        CommandTag: 0x11
        :param memory_id: External memory id
        :param address: the address of configuration block
        '''
        logging.info('TX-CMD: ConfigureMemory [ memoryId=0x%08X | Address=0x%08X ]', memory_id, address)
        # Prepare ConfigureMemory command
        cmd = struct.pack('<4B2I', CommandTag.CONFIGURE_MEMORY, 0x00, 0x00, 0x02, memory_id, address)
        # Process ConfigureMemory command
        raw_value = self._itf_.write_cmd(cmd)

    def reliable_update(self, address):
        '''Checks the validity of backup application at <addr>, then copies the contents of 
        backup application from <addr> to main application region
        CommandTag: 0x12
        :param address: The address is the write address of the application(such as led demo file)
        '''
        logging.info('TX-CMD: ReliableUpdate [ Address=0x%08X ]', address)
        # Prepare ReliableUpdate command
        cmd = struct.pack('<4BI', CommandTag.RELIABLE_UPDATE, 0x00, 0x00, 0x01, address)
        # Process ReliableUpdate command(status_success = RELIABLE_UPDATE_SUCCESS, this is different from other commands)
        raw_value = self._itf_.write_cmd(cmd, status_success=StatusCode.RELIABLE_UPDATE_SUCCESS)

    def generate_key_blob(self, dek_file, blob_file = None):
        '''Generate the blob for the given dek key -- dek.bin, and write the blob to the file -- blob.bin. 
        DEK key file is generated by CST tool.
        CommandTag: 0x13
        :param dek_file: the file contain dek key
        :param blob_file: File for receiving the blob
        '''
        dek_data, _ = read_file(dek_file, 'no_address')
        # blob_data, _ = read_file(blob_file)
        # Prepare GenerateKeyBlob command
        logging.info('TX-CMD: GenerateKeyBlob [ dekFile=%s | blobFile=%s ]', dek_file, blob_file)
        # Prepare GenerateKeyBlob command
        cmd = struct.pack('<4B3I', CommandTag.GENERATE_KEY_BLOB, 0x01, 0x00, 0x03, 0x00, len(dek_data), 0x0)
        # get max packet size
        max_packet_size = self.get_property(PropertyTag.MAX_PACKET_SIZE)
        # Process GenerateKeyBlob command
        self._itf_.write_cmd(cmd)
        # Process Write Data
        self._itf_.write_data(dek_data, max_packet_size)

        # Prepare GenerateKeyBlob command
        blob_len = 0x48
        cmd = struct.pack('<4B3I', CommandTag.GENERATE_KEY_BLOB, 0x00, 0x00, 0x03, 0x0, blob_len, 0x01)
        # Process GenerateKeyBlob command
        self._itf_.write_cmd(cmd)
        data = self._itf_.read_data(blob_len)
        if blob_file:
            write_file(blob_file, data)

    def key_provisioning(self, operation, arg1=None, arg2=None, arg3=None):
        '''The key-provisioning command is a pack of several security related commands.
        • enroll
        Example: -- key-provisioning enroll
        Enroll key provisioning feature. No argument for this operation
        • set_user_key <type><file>[,<size>]
        Example: -- key-provisioning set_user_key 0xB userKey.bin
        Send the user key specified by <type> to bootloader. <file> is the binary file containing user key plain text. If <size> is not specified,
        the entire <file> will be sent, otherwise, blhost only sends the first <size> bytes
        • set_key <type> <size>
        Example: -- key-provisioning set_key 0x1 0x100
        Generate <size> bytes of the key specified by <type>
        • write_key_nonvolatile [memoryID]
        Example: -- key-provisioning write_key_nonvolatile 0x110
        Write the key to a nonvolatile memory
        • read_key_nonvolatile [memoryID]
        Example: -- key-provisioning read_key_nonvolatile 0x110
        Load the key from a nonvolatile memory to bootloader
        • write_key_store <file>[,<size>]
        Send the key store to bootloader. <file> is the binary file containing key store. If <size> is not specified, the entire <file> will be
        sent. Otherwise, only send the first <size> bytes
        • read_key_store <file>
        Read the key store from bootloader to host(PC). <file> is the binary file to store the key store
        blhost Utility application
        CommandTag: 0x15
        :param operation: Performed operation, including 'enroll', 'set_user_key', 'set_key', 
        'write_key_nonvolatile', 'read_key_nonvolatile', 'write_key_store', read_key_store
        :param arg1: According to the corresponding operation, please refer to the above description
        :param arg2: According to the corresponding operation, please refer to the above description
        :param arg3: According to the corresponding operation, please refer to the above description
        :param arg4: According to the corresponding operation, please refer to the above description
        '''
        try:
            k_op = KeyOperation[operation.lower()].value
        except KeyError:
            raise McuBootGenericError('invalid operation arguments: {}'.format(operation))
        
        # Prepare KeyProvisioning command
        logging.info('TX-CMD: KEY_PROVISIONING [ operation=%s ]', operation)
        # Prepare KeyProvisioning command
        if k_op == KeyOperation.enroll:
            cmd = struct.pack('<4BI', CommandTag.KEY_PROVISIONING, 0x00, 0x00, 0x01, k_op)
            # Process KeyProvisioning command
            self._itf_.write_cmd(cmd)
        elif k_op == KeyOperation.set_user_key:
            if not arg1 or not arg2:
                raise McuBootGenericError('invalid {} arguments'.format(operation))
            key_type = arg1
            key_file = arg2
            if arg3 is None:
                data, _ = read_file(key_file, 'no_address')
                length = len(data)
            else:
                data, _ = read_file(key_file, 'no_address')
                length = arg3
                data = data[:length]

            cmd = struct.pack('<4B3I', CommandTag.KEY_PROVISIONING, 0x01, 0x00, 0x03, k_op, key_type, length)
            # get max packet size
            max_packet_size = self.get_property(PropertyTag.MAX_PACKET_SIZE)
            # Process KeyProvisioning command
            self._itf_.write_cmd(cmd)
            # Process Write Data
            self._itf_.write_data(data, max_packet_size)
        elif k_op == KeyOperation.set_key:
            if not arg1 or not arg2 or arg3 is not None:
                raise McuBootGenericError('invalid {} arguments'.format(operation))
            key_type = arg1
            key_size = arg2
            cmd = struct.pack('<4B3I', CommandTag.KEY_PROVISIONING, 0x00, 0x00, 0x02, k_op, key_type, key_size)
            # Process KeyProvisioning command
            self._itf_.write_cmd(cmd)
        elif k_op == KeyOperation.write_key_nonvolatile:
            if arg2 is not None or arg3 is not None:
                raise McuBootGenericError('invalid {} arguments'.format(operation))
            if arg1 is None:
                memory_id = 0
            else:
                memory_id = arg1
            cmd = struct.pack('<4B2I', CommandTag.KEY_PROVISIONING, 0x00, 0x00, 0x02, k_op, memory_id)
            # Process KeyProvisioning command
            self._itf_.write_cmd(cmd)
        elif k_op == KeyOperation.read_key_nonvolatile:
            if arg2 is not None or arg3 is not None:
                raise McuBootGenericError('invalid {} arguments'.format(operation))
            if arg1 is None:
                memory_id = 0
            else:
                memory_id = arg1
            cmd = struct.pack('<4B2I', CommandTag.KEY_PROVISIONING, 0x00, 0x00, 0x02, k_op, memory_id)
            # Process KeyProvisioning command
            self._itf_.write_cmd(cmd)
        elif k_op == KeyOperation.write_key_store:
            if not arg1 or arg3 is not None:
                raise McuBootGenericError('invalid {} arguments'.format(operation))
            key_type = 0x0
            key_file = arg1
            if arg2 is None:
                data, _ = read_file(key_file, 'no_address')
                length = len(data)
            else:
                data, _ = read_file(key_file, 'no_address')
                length = arg2
                data = data[:length]
            cmd = struct.pack('<4B3I', CommandTag.KEY_PROVISIONING, 0x01, 0x00, 0x03, k_op, key_type, length)
            # get max packet size
            max_packet_size = self.get_property(PropertyTag.MAX_PACKET_SIZE)
            # Process KeyProvisioning command
            self._itf_.write_cmd(cmd)
            # Process Write Data
            self._itf_.write_data(data, max_packet_size)
        elif k_op == KeyOperation.read_key_store:
            if not arg1 or arg2 is not None or arg3 is not None:
                raise McuBootGenericError('invalid {} arguments'.format(operation))
            key_file = arg1
            cmd = struct.pack('<4BI', CommandTag.KEY_PROVISIONING, 0x00, 0x00, 0x01, k_op)
            # Process KeyProvisioning command
            length = self._itf_.write_cmd(cmd)
            # Process Write Data
            data = self._itf_.read_data(length)

            write_file(key_file, data)
            logging.info("Successfully saved into: {}".format(key_file))

    def flash_image(self, filename, erase='none', memory_id=0):
        '''Write the formatted image in <file> to the memory specified by memoryID.
        CommandTag: 0x16
        :param filename: The file to be written, supported file types are S-Record (.srec and .s19), and Hex (.hex)
        :param erase: Whether to erase before writing, there are two values ​​of 'erase' and 'none', and numbers are not supported.
        :param memory_id: External memory id
        '''
        if isinstance(erase, int):
            memory_id = erase
            erase = False

        data, address = read_file(filename, None)
        data_len = len(data)
        if data_len == 0:
            raise ValueError('Data len is zero')

        if erase == 'erase':
            sector_size = self.get_property(PropertyTag.FLASH_SECTOR_SIZE, memory_id)
            erase_len = Flash.align_up(data_len, sector_size)
            self.flash_erase_region(address, erase_len, memory_id)
        elif erase == 'none':
            pass
        else:
            raise McuBootGenericError('invalid arguments: {}'.format(erase))

        logging.info('TX-CMD: FlashImage [ filename=%s -> 0x%08X | erase=%s | memoryId = 0x%X ]', filename, address, erase, memory_id)
        # Prepare WriteMemory command
        cmd = struct.pack('<4B3I', CommandTag.WRITE_MEMORY, 0x00, 0x00, 0x03, address, data_len, memory_id)
        # get max packet size
        max_packet_size = self.get_property(PropertyTag.MAX_PACKET_SIZE, memory_id)
        # Process WriteMemory command
        self._itf_.write_cmd(cmd)
        # Process Write Data
        return self._itf_.write_data(data, max_packet_size)

