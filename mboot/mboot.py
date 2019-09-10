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
from .enums import CommandTag, PropertyTag, StatusCode, ExtMemPropTags
from .constant import Interface, KeyOperation
from .tool import read_file, write_file, check_key, atos, size_fmt
from .exception import McuBootGenericError, McuBootCommandError
from .uart import UART
from .usb import RawHID
from .spi import SPI
from .i2c import I2C
from .memorytool import MemoryBlock, Memory, Flash
from .peripheral import parse_port, peripheral_speed
from .decorator import clock

########################################################################################################################
# Helper functions
########################################################################################################################

def decode_property_value(property_tag, raw_value, last_cmd_response=None, memory_id=None):
    if property_tag in (PropertyTag.CURRENT_VERSION, PropertyTag.TARGET_VERSION):
        str_value = "{0:d}.{1:d}.{2:d}".format((raw_value >> 16) & 0xFF, (raw_value >> 8) & 0xFF, raw_value & 0xFF)

    elif property_tag == PropertyTag.AVAILABLE_PERIPHERALS:
        str_value = []
        for key, value in McuBoot.INTERFACES.items():
            if value[0] & raw_value:
                str_value.append(key)

    elif property_tag in (PropertyTag.CRC_CHECK_STATUS, PropertyTag.QSPI_INIT_STATUS,
                          PropertyTag.RELIABLE_UPDATE_STATUS):
        if raw_value in StatusCode:
            str_value = StatusCode[raw_value]
        else:
            str_value = 'Unknown Status Code: 0x{:08X}'.format(raw_value)

    elif property_tag == PropertyTag.VERIFY_WRITES:
        str_value = 'ON' if raw_value else 'OFF'

    elif property_tag == PropertyTag.RESERVED_REGIONS:
        word_len = int((len(last_cmd_response) - 8) / 4)
        result = struct.unpack_from('<{:d}I'.format(word_len), last_cmd_response, 8)
        str_value = []
        for i in range(0, len(result), 2):
            block = MemoryBlock(result[i], result[i+1])
            if block:
                str_value.append(str(block))

    elif property_tag == PropertyTag.UNIQUE_DEVICE_IDENT:
        word_len = int((len(last_cmd_response) - 8) / 4)
        result = struct.unpack_from('<{:d}I'.format(word_len), last_cmd_response, 8)
        str_list = ['{:08X}'.format(value) for value in result]
        str_value = ' '.join(str_list)
        # str_value = '{:04X} {:04X} '.format((raw_value >> 16) & 0xFFFF, raw_value & 0xFFFF)

    elif property_tag == PropertyTag.FLASH_FAC_SUPPORT:
        str_value = 'SUPPORTED' if raw_value else 'UNSUPPORTED'

    elif property_tag == PropertyTag.FLASH_SECURITY_STATE:
        security_state = {0x00000000: 'Unlocked', 0x00000001: 'Locked', 0x5AA55AA5: 'Unlocked', 0xC33CC33C: 'Locked'}
        if raw_value in security_state:
            str_value = security_state[raw_value]
        else:
            str_value = "Unknown (0x{:08X})".format(raw_value)

    elif property_tag == PropertyTag.AVAILABLE_COMMANDS:
        str_value = []
        for name, value, desc in CommandTag:
            if (1 << value) & raw_value:
                str_value.append(name)

    elif property_tag in (PropertyTag.MAX_PACKET_SIZE, PropertyTag.FLASH_SECTOR_SIZE,
                          PropertyTag.FLASH_SIZE, PropertyTag.RAM_SIZE, PropertyTag.FLASH_ACCESS_SEGMENT_SIZE):
        str_value = size_fmt(raw_value)

    elif property_tag in (PropertyTag.RAM_START_ADDRESS, PropertyTag.FLASH_START_ADDRESS,
                          PropertyTag.SYSTEM_DEVICE_IDENT):
        str_value = '0x{:08X}'.format(raw_value)

    elif property_tag in (PropertyTag.FLASH_ACCESS_SEGMENT_COUNT, PropertyTag.FLASH_BLOCK_COUNT,
                          PropertyTag.VALIDATE_REGIONS):
        str_value = '0x{:X}'.format(raw_value)

    elif property_tag == PropertyTag.FLASH_READ_MARGIN:
        margin_info = {0: "Normal", 1: "User", 2: "Factory"}
        if raw_value in margin_info:
            str_value = "{} (0x{:X})".format(margin_info[raw_value], raw_value)
        else:
            str_value = "Unknown (0x{:X})".format(raw_value)

    elif property_tag == PropertyTag.EXTERNAL_MEMORY_ATTRIBUTES and memory_id:

        result = struct.unpack_from('<6I', last_cmd_response, 8)
        prop_tags, start_address, total_size, page_size, sector_size, block_size = result
        str_value = []
        str_value.append('Memory Id: 0x{:X}'.format(memory_id))
        if prop_tags & ExtMemPropTags.START_ADDRESS:
            str_value.append('Start Address: 0x{:08X}'.format(start_address))

        if prop_tags & ExtMemPropTags.SIZE_IN_KBYTES:
            str_value.append('Total Size: {}'.format(size_fmt(total_size * 1024)))

        if prop_tags & ExtMemPropTags.PAGE_SIZE:
            str_value.append('Page Size: {}'.format(size_fmt(page_size)))

        if prop_tags & ExtMemPropTags.SECTOR_SIZE:
            str_value.append('Sector Size: {}'.format(size_fmt(sector_size)))

        if prop_tags & ExtMemPropTags.BLOCK_SIZE:
            str_value.append('Block Size: {}'.format(size_fmt(block_size)))

    elif property_tag == PropertyTag.IRQ_NOTIFIER_PIN:
        pin = raw_value & 0xFF
        port = (raw_value >> 8) & 0xFF
        enabled = True if raw_value & (1 << 32) else False
        if enabled:
            str_value = "Irq pin is enabled, using GPIO port[{}], pin[{}]".format(port, pin)
        else:
            str_value = "Irq pin is disabled"

    elif property_tag == PropertyTag.PFR_KEYSTORE_UPDATE_OPT:
        str_value = "FFR KeyStore Update is "

        if raw_value == 0:
            str_value += "Key Provisioning"
        elif raw_value == 1:
            str_value += "Write Memory"
        else:
            str_value += "UnKnow Option"

    else:
        str_value = '0x{:X}'.format(raw_value)

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

    def __init__(self, level=logging.WARNING):
        self.cli_mode = False
        self._itf_ = None
        self.current_interface = None
        self.reopen_args = None
        self.timeout = 1
        self.memory = None
        self.flash = None
        # self._pg_func = None
        # self._pg_start = 0
        # self._pg_end = 100
        # self._abort = False
        logging.basicConfig(level=level)

    # @staticmethod
    # def _parse_status(data):
    #     return unpack_from('<I', data, 4)[0]

    # @staticmethod
    # def _parse_value(data):
    #     return unpack_from('<I', data, 8)[0]

    # def set_handler(self, progressbar, start_val=0, end_val=100):
    #     self._pg_func = progressbar
    #     self._pg_start = start_val
    #     self._pg_end = end_val
    # def abort(self):
    #     self._abort = True

    def __bool__(self):
        return bool(self._itf_)

    def is_open(self):
        """ MCUBoot: Check if device connected
        """
        if self._itf_ is not None:
            return True
        else:
            return False

    def open_usb(self, vid_pid, path=None):
        """ MCUBoot: Connect by USB
        :param vid_pid: Device vid and pid, support str or tuple, such as 'vid pid', (vid, pid)
        :param path: You need to specify additional paths when you insert two devices with the same vid, PID at the same time,
        on linux: str '0,5' or tuple '(0,5)' represent 'Bus 000 Address 005', on windows: the value of bus relations, such as '6&28e6394a&0&0000',
        This function is not involved in library function calls, it is used in cli mode
        :return The result of opening the device
        """
        if isinstance(vid_pid, str):
            _vid_pid = parse_port(Interface.USB.name, vid_pid)
        else:   # Default input tuple in cli mode, no conversion required
            if len(vid_pid) == 2:
                _vid_pid = vid_pid
            elif len(vid_pid) == 3 and path is None:
                path = vid_pid[-1]
                _vid_pid = vid_pid[:2]
            else:
                raise ValueError('vid_pid input error!')

        dev = RawHID.enumerate(*_vid_pid, path)
        if len(dev) == 1:
            logging.info('Connect: %s', dev[0].info())
            self._itf_ = dev[0] # Already open, simple assignment
            self._itf_.open()
            self.current_interface = Interface.USB
            self.reopen_args = vid_pid
            return True
        elif len(dev) > 1:
            raise McuBootGenericError("You need to specify additional paths when you insert two devices with the same vid, PID at the same time")
        else:
            info = 'Can not find vid,pid: 0x{p[0]:04X}, 0x{p[1]:04X}'.format(p=_vid_pid)
            if self.cli_mode:   # Fast failure in cli mode
                raise McuBootGenericError(info)
            logging.info(info)
            return False

    def open_uart(self, port, baudrate=peripheral_speed['uart']):
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
    
    def open_spi(self, vid_pid, index=1, freq=peripheral_speed['spi'], mode=0):
        """ MCUBoot: Connect by UART
        """
        if isinstance(vid_pid, str):
            # _vid_pid = parse_port(Interface.SPI.name, vid_pid)
            _vid_pid, _freq = parse_peripheral(peripheral, args)
        else:   # Default input tuple in cli mode, no conversion required
            _vid_pid = vid_pid
        try:
            self._itf_ = SPI(freq, mode)
            index = index or 1
            self._itf_.open(*_vid_pid, index=index)
        except Exception:
            logging.info('Open SPI failed, SPI disconnected !')
            if self.cli_mode:   # Fast failure in cli mode
                raise
            return False
        else:
            self.current_interface = Interface.SPI
            self.reopen_args = (_vid_pid, freq, mode)
            return True

    def open_i2c(self, vid_pid, index=1, freq=peripheral_speed['i2c']):
        """ MCUBoot: Connect by UART
        """
        if isinstance(vid_pid, str):
            _vid_pid = parse_port(Interface.I2C.name, vid_pid)
        else:   # Default input tuple in cli mode, no conversion required
            _vid_pid = vid_pid
        try:
            self._itf_ = I2C(freq)
            index = index or 1
            self._itf_.open(*_vid_pid, index=index)
        except Exception:
            logging.info('Open I2C failed, I2C disconnected !')
            if self.cli_mode:   # Fast failure in cli mode
                raise
            return False
        else:
            self.current_interface = Interface.I2C
            self.reopen_args = (_vid_pid, freq)
            return True

    def close(self):
        """ MCUBoot: Disconnect device
        """
        if self._itf_:
            self._itf_.close()
            self._itf_ = None
            # can't reopen
            # self.current_interface = None
            # self.reopen_args = None
            return True
        else:
            return False
    
    def get_memory_range(self):
        try:
            mstart = self.get_property(PropertyTag.RAM_START_ADDRESS)
            mlength = self.get_property(PropertyTag.RAM_SIZE)
            self.memory = Memory(mstart, None, mlength)
            fstart = self.get_property(PropertyTag.FLASH_START_ADDRESS)
            flength = self.get_property(PropertyTag.FLASH_SIZE)
            self.flash = Flash(fstart, None, flength)
        except McuBootCommandError:
            pass    # Some device have no internal memory.

    def is_in_memory(self, block):
        return block in self.memory if self.memory else True

    def is_in_flash(self, block):
        return block in self.flash if self.flash else True

    def get_mcu_info(self, memory_id=0):
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
                str_value = decode_property_value(property_tag, raw_value, self._itf_.last_cmd_response, memory_id)
            except McuBootCommandError:
                continue
            mcu_info.update({property_name: str_value})

        return mcu_info

    def get_exmemory_info(self, memory_id):
        '''Use special tag EXTERNAL_MEMORY_ATTRIBUTES(0x19) to get information about external memory'''
        exmem_info = {}
        try:
            raw_value = self.get_property(PropertyTag.EXTERNAL_MEMORY_ATTRIBUTES, memory_id)
            str_value = decode_property_value(PropertyTag.EXTERNAL_MEMORY_ATTRIBUTES, raw_value, self._itf_.last_cmd_response, memory_id)
        except McuBootCommandError:
            pass
        # str_list = [' External Memory Attributes:']
        # str_list.extend([' ' + value.strip() for value in str_value.split('\n')])
        # str_value = '\n '.join(str_list)
        exmem_info.update({'External Memory Attributes': str_value})
        return exmem_info

    def setup_external_memory(self, memory_id, exconf):
        start_config_address = fill_config_address = exconf[0]
        external_config = exconf[1:]
        for word in external_config:
            self.fill_memory(fill_config_address, 4, word)
            fill_config_address += 4
        self.configure_memory(memory_id, start_config_address)

    def flash_erase_all(self, memory_id = 0):
        """ MCUBoot: Erase complete flash memory without recovering flash security section
        CommandTag: 0x01
        :param memory_id: External memory id
        """
        logging.info('TX-CMD: FlashEraseAll [ memoryId = 0x%X ]', memory_id)
        # Prepare FlashEraseAll command
        cmd = struct.pack('4BI', CommandTag.FLASH_ERASE_ALL, 0x00, 0x00, 0x01, memory_id)
        # Process FlashEraseAll command
        timeout = 300 if self.timeout == 1 else self.timeout
        self._itf_.write_cmd(cmd, timeout = timeout)

    '''                             
    MT64 UART 57600
    len             size    time
    0x00010000      64K     0.02749509
    0x00100000      1M      0.03662174
    0x01000000      16M     0.47802436
    '''
    # @clock
    def flash_erase_region(self, start_address, length, memory_id = 0):
        """ MCUBoot: Erase specified range of flash
        CommandTag: 0x02
        :param start_address: Start address
        :param length: Count of bytes
        :param memory_id: External memory id
        """
        logging.info('TX-CMD: FlashEraseRegion [ StartAddr=0x%08X | len=0x%X | memoryId = 0x%X ]', start_address, length, memory_id)
        # Prepare FlashEraseRegion command
        cmd = struct.pack('<4B3I', CommandTag.FLASH_ERASE_REGION, 0x00, 0x00, 0x03, start_address, length, memory_id)
        # Process FlashEraseRegion command
        timeout = 300 if self.timeout == 1 else self.timeout
        self._itf_.write_cmd(cmd, timeout = timeout)

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
        else:
            key = backdoor_key
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
        # print(CommandTag.GET_PROPERTY[prop_tag])
        cmd = struct.pack('<4B2I', CommandTag.GET_PROPERTY, 0x00, 0x00, 0x02, prop_tag, memory_id)
        # Process FillMemory command
        raw_value = self._itf_.write_cmd(cmd)

        logging.info('RX-CMD: %s = %s', PropertyTag[prop_tag], decode_property_value(prop_tag, 
            raw_value, self._itf_.last_cmd_response, memory_id))
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

        # the reset command waits for different time to prevent the device from executing the next instruction when it is not ready
        # but this does not solve the problem of calling through other scripts, which will be resolved in future versions.
        if self.cli_mode == False:
            '''
            uart-57600: 0.01s
            uart-115200:0.009s
            SPI-1M:     0.005s
            I2C-100K:   No need to wait
            '''
            if self.current_interface == Interface.USB:
                self._itf_.close()
                time.sleep(0.4)
                self.open_usb(self.reopen_args)
            elif self.current_interface == Interface.UART:
                time.sleep(0.01)    # Wait 10 ms for the device to complete reset
            elif self.current_interface == Interface.SPI:
                time.sleep(0.005)   # Wait 5 ms for the device to complete reset
            # elif self.current_interface == Interface.I2C:
            #     time.sleep(0.001)   # Wait 5 ms for the device to complete reset

    def flash_erase_all_unsecure(self):
        """ MCUBoot: Erase complete flash memory and recover flash security section
        CommandTag: 0x0D
        """
        logging.info('TX-CMD: FlashEraseAllUnsecure')
        # Prepare FlashEraseAllUnsecure command
        cmd = struct.pack('4B', CommandTag.FLASH_ERASE_ALL_UNSECURE, 0x00, 0x00, 0x00)
        # Process FlashEraseAllUnsecure command
        timeout = 300 if self.timeout == 1 else self.timeout
        self._itf_.write_cmd(cmd, timeout = timeout)

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

