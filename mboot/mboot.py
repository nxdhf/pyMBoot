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
from .misc import atos, size_fmt
from .tool import read_file, write_file
# from .protocol import UartProtocol, UsbProtocol, FPType
from .exception import McuBootGenericError, McuBootCommandError
from .uart import UART
from .usb import RawHID
from .spi import SPI
from .memorytool import MemoryBlock, Memory, Flash

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
# KBoot interfaces
########################################################################################################################

# DEVICES = {
#     # NAME   | VID   | PID
#     'MKL27': (0x15A2, 0x0073),
#     'LPC55': (0x1FC9, 0x0021),
#     'K82F' : (0x15A2, 0x0073),
#     '232h' : (0x403,0x6014)
# }


# def scan_usb(device_name=None):
#     """ KBoot: Scan commected USB devices
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


def scan_uart():
    raise NotImplemented("Function is not implemented")

def scan_uart():
    raise NotImplemented("Function is not implemented")


########################################################################################################################
# McuBoot Class
########################################################################################################################

class McuBoot(object):

    INTERFACES = {
        #  KBoot Interface | mask | default speed
        'UART':      [0x00000001, 115200],
        'I2C-Slave': [0x00000002, 400],
        'SPI-Slave': [0x00000004, 400],
        'CAN':       [0x00000008, 500],
        'USB-HID':   [0x00000010, 12000000],
        'USB-CDC':   [0x00000020, 12000000],
        'USB-DFU':   [0x00000040, 12000000],
    }

    def __init__(self):
        self._itf_ = None
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
        """ KBoot: Check if device connected
        """
        if self._usb_dev is not None:
            return True
        else:
            return False

    def open_usb(self, dev):
        """ KBoot: Connect by USB
        """
        if dev is not None:
            logging.info('Connect: %s', dev.info())
            self._itf_ = dev
            self._itf_.open()
            # self.protocol = UsbProtocol(self._itf_)

            return True
        else:
            logging.info('USB Disconnected !')
            return False

    def open_uart(self, port, baudrate):
        """ KBoot: Connect by UART
        """
        if port is not None:
            self._itf_ = UART()
            self._itf_.open(port, baudrate)
            # if self._uart_dev.ping():
            #     return True
            # else:
            #     self.close()
            #     return False
            return True
        else:
            logging.info('UART Disconnected !')
            return False
    
    def open_spi(self, info, freq, mode):
        """ KBoot: Connect by UART
        """
        if info is not None:
            self._itf_ = SPI(freq, mode)
            self._itf_.open(*info)
            # self.protocol = UartProtocol(self._itf_)
            return True
        else:
            logging.info('SPI Disconnected !')
            return False

    def close(self):
        """ KBoot: Disconnect device
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
        """ KBoot: Get MCU info (available properties collection)
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
        """ KBoot: Erase complete flash memory without recovering flash security section
        CommandTag: 0x01
        """
        logging.info('TX-CMD: FlashEraseAll [ memoryId = 0x%X ]', memory_id)
        # Prepare FlashEraseAll command
        cmd = struct.pack('4BI', CommandTag.FLASH_ERASE_ALL, 0x00, 0x00, 0x00, memory_id)
        # Process FlashEraseAll command
        self._itf_.write_cmd(cmd)

    def flash_erase_region(self, start_address, length, memory_id = 0):
        """ KBoot: Erase specified range of flash
        CommandTag: 0x02
        :param start_address: Start address
        :param length: Count of bytes
        """
        logging.info('TX-CMD: FlashEraseRegion [ StartAddr=0x%08X | len=0x%X | memoryId = 0x%X ]', start_address, length, memory_id)
        # Prepare FlashEraseRegion command
        cmd = struct.pack('<4B3I', CommandTag.FLASH_ERASE_REGION, 0x00, 0x00, 0x02, start_address, length, memory_id)
        # Process FlashEraseRegion command
        self._itf_.write_cmd(cmd, self.timeout)

    def read_memory(self, start_address, length, filename = None, memory_id = 0):
        """ KBoot: Read data from MCU memory
        CommandTag: 0x03
        :param start_address: Start address
        :param length: Count of bytes
        :return List of bytes
        """
        if length == 0:
            raise ValueError('Data len is zero')
        try:
            temp = int(filename, 0)
        except Exception:
            pass
        else:
            filename = None
            memory_id = temp
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
        """ KBoot: Write data into MCU memory
        CommandTag: 0x04
        :param start_address: Start address
        :param data: List of bytes
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
        # Process WriteMemory command
        self._itf_.write_cmd(cmd)
        # Process Write Data
        return self._itf_.write_data(data)

    def fill_memory(self, start_address, length, pattern=0xFFFFFFFF, unit='word'):
        """ KBoot: Fill MCU memory with specified pattern
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
        """ KBoot: Disable flash security by backdoor key
        CommandTag: 0x06
        :param backdoor_key:
        """
        logging.info('TX-CMD: FlashSecurityDisable [ backdoor_key [0x] = %s ]', atos(backdoor_key))
        # Prepare FlashSecurityDisable command
        cmd = struct.pack('4B', CommandTag.FLASH_SECURITY_DISABLE, 0x00, 0x00, 0x02)
        if len(backdoor_key) < 8:
            raise ValueError('Short range of backdoor key')
        cmd += bytes(backdoor_key[3::-1])
        cmd += bytes(backdoor_key[:3:-1])
        # Process FlashSecurityDisable command
        self._itf_.write_cmd(cmd)

    def get_property(self, prop_tag, memory_id = 0):
        """ KBoot: Get value of specified property
        CommandTag: 0x07
        :param prop_tag: The property ID (see Property enumerator)
        :param memory_id:
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
        """ KBoot: Set value of specified property
        CommandTag: 0x0C
        :param  property_tag: The property ID (see Property enumerator)
        :param  value: The value of selected property
        """
        logging.info('TX-CMD: SetProperty->%s = %d [ memoryId = 0x%X ]', PropertyTag[prop_tag], value, memory_id)
        # Prepare SetProperty command
        cmd = struct.pack('<4B3I', CommandTag.SET_PROPERTY, 0x00, 0x00, 0x02, prop_tag, value, memory_id)
        # Process SetProperty command
        self._itf_.write_cmd(cmd)

    def receive_sb_file(self, data):
        """ KBoot: Receive SB file
        CommandTag: 0x08
        :param  data: SB file data
        """
        if len(data) == 0:
            raise ValueError('Data len is zero')
        logging.info('TX-CMD: Receive SB file [ len=%d ]', len(data))
        # Prepare WriteMemory command
        cmd = struct.pack('<4BI', CommandTag.RECEIVE_SB_FILE, 0x00, 0x00, 0x02, len(data))
        # Process WriteMemory command
        self._itf_.write_cmd(cmd)
        # Process Write Data
        return self._itf_.write_data(data)

    def execute(self, jump_address, argument, sp_address):
        """ KBoot: Fill MCU memory with specified pattern
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

    def call(self, call_address, argument, sp_address):
        """ KBoot: Fill MCU memory with specified pattern
        CommandTag: 0x0A
        :param call_address: Call address (must be word aligned)
        :param argument: Function arguments address
        :param sp_address: Stack pointer address
        """
        logging.info('TX-CMD: Call [ CallAddr=0x%08X | ARG=0x%08X  | SP=0x%08X ]', call_address, argument, sp_address)
        # Prepare Call command
        cmd = struct.pack('<4B3I', CommandTag.CALL, 0x00, 0x00, 0x03, call_address, argument, sp_address)
        # Process Call command
        self._itf_.write_cmd(cmd)

    def reset(self):
        """ KBoot: Reset MCU
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
        time.sleep(0.005)   # Wait 5 ms for the device to complete reset
                

    def flash_erase_all_unsecure(self):
        """ KBoot: Erase complete flash memory and recover flash security section
        CommandTag: 0x0D
        """
        logging.info('TX-CMD: FlashEraseAllUnsecure')
        # Prepare FlashEraseAllUnsecure command
        cmd = struct.pack('4B', CommandTag.FLASH_ERASE_ALL_UNSECURE, 0x00, 0x00, 0x00)
        # Process FlashEraseAllUnsecure command
        self._itf_.write_cmd(cmd)

    def flash_read_once(self, index, length):
        """ KBoot: Read from MCU flash program once region (max 8 bytes)
        CommandTag: 0x0F
        :param index: Start index
        :param length: Count of bytes
        :return List of bytes
        """
        if (index + length) > 8:
            length = 8 - index
        if length == 0:
            raise ValueError('Index out of range')
        logging.info('TX-CMD: FlashReadOnce [ Index=%d | len=%d ]', index, length)
        # Prepare FlashReadOnce command
        cmd = struct.pack('<4B2I', CommandTag.FLASH_READ_ONCE, 0x00, 0x00, 0x02, index, length)
        # Process FlashReadOnce command
        self._itf_.write_cmd(cmd)
        # Process Read Data
        return self._itf_.read_data(length)

    def flash_program_once(self, index, data):
        """ KBoot: Write into MCU flash program once region (max 8 bytes)
        CommandTag: 0x0E
        :param index: Start index
        :param data: List of bytes
        """
        length = len(data)
        if (index + length) > 8:
            length = 8 - index
        if length == 0:
            raise ValueError('Index out of range')
        logging.info('TX-CMD: FlashProgramOnce [ Index=%d | Data[0x]: %s ]', index, atos(data[:length]))
        # Prepare FlashProgramOnce command
        cmd = struct.pack('<4B2I', CommandTag.FLASH_PROGRAM_ONCE, 0x00, 0x00, 0x03, index, length)
        cmd += bytes(data)
        # Process FlashProgramOnce command
        self._itf_.write_cmd(cmd)
        return length

    def flash_read_resource(self, start_address, length, option=1):
        """ KBoot: Read resource of flash module
        CommandTag: 0x10
        :param start_address:
        :param length:
        :param option:
        :return resource list
        """
        logging.info('TX-CMD: FlashReadResource [ StartAddr=0x%08X | len=%d ]', start_address, length)
        # Prepare FlashReadResource command
        cmd = struct.pack('<4B3I', CommandTag.FLASH_READ_RESOURCE, 0x00, 0x00, 0x03, start_address, length, option)
        # Process FlashReadResource command
        raw_value = self._itf_.write_cmd(cmd)
        rx_len = raw_value
        length = min(length, rx_len)
        # Process Read Data
        return self._itf_.read_data(length)

    def configure_memory(self, memory_id, address):
        '''KBoot: Configure external memory
        CommandTag: 0x11
        :param memory_id: external memory id
        :param address: the address of configuration block
        '''
        logging.info('TX-CMD: ConfigureMemory [ memoryId=0x%08X | Address=0x%08X ]', memory_id, address)
        # Prepare ConfigureMemory command
        cmd = struct.pack('<4B2I', CommandTag.CONFIGURE_MEMORY, 0x00, 0x00, 0x02, memory_id, address)
        # Process ConfigureMemory command
        raw_value = self._itf_.write_cmd(cmd)

    def reliable_update(self):
        '''
        CommandTag: 0x12
        '''
        # TODO: Write implementation
        raise NotImplementedError('Function \"reliable_update()\" not implemented yet')

    def generate_key_blob(self, dek_file, blob_file = None):
        '''Generate the blob for the given dek key -- dek.bin, and write the blob to the file -- blob.bin. 
        DEK key file is generated by CST tool.
        CommandTag: 0x13
        :param dek_file: the file contain dek key
        :param blob_file: File for receiving the blob
        '''
        dek_data, _ = read_file(dek_file, 'no_address')
        # blob_data, _ = read_file(blob_file)
        # Prepare ConfigureMemory command
        logging.info('TX-CMD: GenerateKeyBlob [ dekFile=%s | blobFile=%s ]', dek_file, blob_file)
        # Prepare GenerateKeyBlob command
        cmd = struct.pack('<4B3I', CommandTag.GENERATE_KEY_BLOB, 0x01, 0x00, 0x03, 0x00, len(dek_data), 0x0)
        # Process GenerateKeyBlob command
        self._itf_.write_cmd(cmd)
        # Process Write Data
        self._itf_.write_data(dek_data)

        # Prepare ConfigureMemory command
        blob_len = 0x48
        cmd = struct.pack('<4B3I', CommandTag.GENERATE_KEY_BLOB, 0x00, 0x00, 0x03, 0x0, blob_len, 0x01)
        # Process GenerateKeyBlob command
        self._itf_.write_cmd(cmd)
        data = self._itf_.read_data(blob_len)
        if blob_file:
            write_file(blob_file, data)

    def key_provisioning(self):
        '''
        CommandTag: 0x14 ?? 0x15
        '''
        # TODO: Write implementation
        raise NotImplementedError('Function \"key_provisioning()\" not implemented yet')

    def load_image(self):
        '''
        CommandTag: 0x15 ??
        '''
        # TODO: Write implementation
        raise NotImplementedError('Function \"load_image()\" not implemented yet')

