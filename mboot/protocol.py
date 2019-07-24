import array
from enum import Enum
import struct
import logging

from .misc import atos
from .tool import crc16
from .enums import CommandTag, PropertyTag, StatusCode
from .exception import McuBootCommandError, McuBootDataError, McuBootConnectionError, McuBootTimeOutError

class ProtocolMixin(object):
    '''This mixed-in class provides some methods about the protocol part for external calls.
    It will be mixed into aggregate class, such as USB class, Uart class...
    Through inheritance, the class implements code reuse.
    '''
    _start = 0x5A

    # def __init__(self, interface):
    #     self._itf_ = interface

    @staticmethod
    def parse_payload(payload):
        # commandTag, flags, reserved, parameterCount, propertyTag, propertyValue = struct.unpack('<4B2L', payload)
        propertyTag, propertyValue = struct.unpack_from('<2L', payload, 4)
        return propertyValue

    @staticmethod
    def parse_response_payload(payload):
        # response_tag, flags, reserved, parameterCount, status, propertyValue = struct.unpack('<4B2L', payload)
        try:
            status, propertyValue = struct.unpack_from('<2L', payload, 4)
        except struct.error as e:
            status = struct.unpack_from('<L', payload, 4)[0]
            propertyValue = 0   # Should be set to None, but it will cause problems when printing cannot be converted
        return status, propertyValue

class UartProtocolMixin(ProtocolMixin):

    @staticmethod
    def _gen_crc(head, payload):
        crc = crc16(head + payload)
        return array.array('B', [crc & 0xff, crc >> 8 & 0xff])

    @classmethod
    def genPacket(cls, packet_type, payload):
        '''
        :param int packet_type: Currrent packet type
        :parm bytes payload: payload in the current packet
        :returns: The complete packet contains head and payload
        '''
        head = struct.pack('<2BH', cls._start, packet_type, len(payload))
        head += (cls._gen_crc(head, payload))
        return head + payload

    @staticmethod
    def parse_framing(head):
        _, _packet_type, payload_len, crc = struct.unpack('<2B2H', head)
        return _packet_type, crc

    def read_cmd(self, **kwargs):
        '''Receive the command packet (only need to receive the packet when an error occurs)
        Implemented but not called, The process is implemented in read_data, write_data
        '''
        try:
            head, rxpkg = self.read(FPType.CMD, **kwargs)
        except:
            logging.info('RX-CMD: %s Disconnected', self.__class__.__name__)
            raise McuBootTimeOutError('%s Disconnected', self.__class__.__name__)
        
        # log RX raw command data
        logging.debug('RX-CMD [%02d]: %s', len(rxpkg), atos(rxpkg))

        # Parse and validate status flag
        status, value = self.parse_response_payload(rxpkg)
        logging.debug('status: %#x, value: %#x', status, value)
        if status != StatusCode.SUCCESS:
            if StatusCode.is_valid(status):
                logging.debug('TX-CMD: %s', StatusCode[status])
                raise McuBootCommandError(errname=StatusCode[status], errval=status)
            else:
                logging.debug('TX-CMD: Unknown Error %d', status)
                raise McuBootCommandError(errval=status)
        return value

    def write_cmd(self, payload, timeout=1000, status_success=StatusCode.SUCCESS, **kwargs):
        '''Send the cmd packet
        :param bytes payload: payload in the current packet

        '''
        self.ping()
        data = self.genPacket(FPType.CMD, payload)

        # log TX raw command data
        logging.debug('TX-CMD [%02d]: %s', len(data), atos(data))

        self.write(FPType.CMD, data)
        try:
            head, rxpkg = self.read(FPType.CMD, **kwargs)
        except:
            logging.debug('RX-CMD: %s Disconnected', self.__class__.__name__)
            raise McuBootTimeOutError('%s Disconnected', self.__class__.__name__)

        # log RX raw command data
        logging.debug('RX-CMD [%02d]: %s', len(rxpkg), atos(rxpkg))
        self.last_cmd_response = rxpkg

        # Parse and validate status flag
        status, value = self.parse_response_payload(rxpkg)
        logging.debug('status: %#x, value: %#x', status, value)
        if status != status_success:
            if StatusCode.is_valid(status):
                logging.debug('RX-CMD: %s', StatusCode[status])
                raise McuBootCommandError(errname=StatusCode[status], errval=status)
            else:
                logging.debug('RX-CMD: Unknown Error %d', status)
                raise McuBootCommandError(errval=status)
        return value

    def read_data(self, length, timeout=1000):
        n = 0
        data = bytearray()

        while n < length:
            head, pkg = self.read(FPType.DATA)
            _packet_type, crc = self.parse_framing(head)
            
            '''Slave interrupt in read data
            Parse the package and throw the appropriate error'''
            if _packet_type == FPType.CMD:
                status, value = self.parse_response_payload(pkg)
                logging.debug('status: %#x, value: %#x', status, value)
                if status != StatusCode.SUCCESS:
                    if StatusCode.is_valid(status):
                        logging.debug('RX-DATA: %s' % StatusCode.desc(status))
                        raise McuBootDataError(mode='read', errname=StatusCode.desc(status), errval=status)
                    else:
                        logging.debug('RX-DATA: Unknown Error %d' % status)
                        raise McuBootDataError(mode='read', errval=status)
                # else: # end of translate
                #     break
            data.extend(pkg)
            n += len(pkg)
        head, pkg = self.read(FPType.CMD)
        self.last_cmd_response = pkg

        # Parse and validate status flag
        status, value = self.parse_response_payload(pkg)
        logging.debug('status: %#x, value: %#x', status, value)
        if status != StatusCode.SUCCESS:
            if StatusCode.is_valid(status):
                logging.debug('RX-DATA: %s' % StatusCode.desc(status))
                raise McuBootDataError(mode='read', errname=StatusCode.desc(status), errval=status)
            else:
                logging.debug('RX-DATA: Unknown Error %d' % status)
                raise McuBootDataError(mode='read', errval=status)

        logging.info('RX-DATA: Successfully Received %d Bytes', len(data))
        return data

    def write_data(self, data, max_packet_size=0x20):
        n = len(data)
        start = 0
        
        while n > 0:
            end = start + max_packet_size
            data_packet = self.genPacket(FPType.DATA, data[start:end])
            try:
                '''There may be a problem with the write, the slave aborts receiving the data, 
                and the master aborts the write and receives the error message.'''
                self.write(FPType.DATA, data_packet)
            except McuBootDataError as e:
                logging.error(e)
                break
            start = end
            n -= max_packet_size
        head, pkg = self.read(FPType.CMD)
        self.last_cmd_response = pkg

        status, value = self.parse_response_payload(pkg)
        logging.debug('status: %#x, value: %#x', status, value)
        if status != StatusCode.SUCCESS:
            logging.debug('TX-DATA: %s' % StatusCode[status])
            raise McuBootDataError(mode='write', errname=StatusCode[status], errval=status)

        logging.info('TX-DATA: Successfully Send %d Bytes', len(data))
        return start

# class UartProtocol(ProtocolMixin):
#     @staticmethod
#     def _gen_crc(head, payload):
#         crc = crc16(head + payload)
#         return array.array('B', [crc & 0xff, crc >> 8 & 0xff])

#     @classmethod
#     def genPacket(cls, packet_type, payload):
#         '''
#         :param int packet_type: Currrent packet type
#         :parm bytes payload: payload in the current packet
#         :returns: The complete packet contains head and payload
#         '''
#         head = struct.pack('<2BH', cls._start, packet_type, len(payload))
#         head += (cls._gen_crc(head, payload))
#         return head + payload
#     def write_cmd(self, payload, **kwargs):
#         '''Handling the cmd packet to be sent
#         :param bytes payload: payload in the current packet

#         '''
#         self._api.ping()
#         data = self.genPacket(FPType.CMD, payload)

#         # log TX raw command data
#         logging.debug('TX-CMD [%02d]: %s', len(data), atos(data))

#         self._api.write(FPType.CMD, data)
#         try:
#             head, rxpkg = self._api.read(FPType.CMD, **kwargs)
#         except:
#             logging.info('RX-CMD: %s Disconnected', self._api.__class__.__name__)
#             raise McuBootTimeOutError('%s Disconnected', self._api.__class__.__name__)

#         # log RX raw command data
#         logging.debug('RX-CMD [%02d]: %s', len(rxpkg), atos(rxpkg))

#         # Parse and validate status flag
#         status, value = self.parse_response_payload(rxpkg)
#         logging.debug('status: %d, value: %d', status, value)
#         if status != StatusCode.SUCCESS:
#             if StatusCode.is_valid(status):
#                 logging.info('RX-CMD: %s', StatusCode[status])
#                 raise McuBootCommandError(errname=StatusCode[status], errval=status)
#             else:
#                 logging.info('RX-CMD: Unknown Error %d', status)
#                 raise McuBootCommandError(errval=status)
#         return value

#     def read_data(self, length, timeout=1000):
#         n = 0
#         data = bytearray()

#         while n < length:
#             _, pkg = self._api.read(FPType.DATA, 0x20+0x6+6)
#             data.extend(pkg)
#             n += 0x20
#         head, pkg = self._api.read(FPType.CMD)

#         # Parse and validate status flag
#         status, value = self.parse_response_payload(pkg)
#         logging.debug('status: %d, value: %d', status, value)
#         if status != StatusCode.SUCCESS:
#             if StatusCode.is_valid(status):
#                 logging.info('RX-DATA: %s' % StatusCode.desc(status))
#                 raise McuBootDataError(mode='read', errname=StatusCode.desc(status), errval=status)
#             else:
#                 logging.info('RX-DATA: Unknown Error %d' % status)
#                 raise McuBootDataError(mode='read', errval=status)

#         logging.info('RX-DATA: Successfully Received %d Bytes', len(data))
#         return data
    
#     def write_data(self, data, max_packet_size=0x20):
#         n = len(data)
#         start = 0
        
#         while n > 0:
#             end = start + max_packet_size
#             data_packet = self.genPacket(FPType.DATA, data[start:end])
#             self._api.write(FPType.DATA, data_packet)
#             start = end
#             n -= max_packet_size
#         head, pkg = self._api.read(FPType.CMD)

#         status, value = self.parse_response_payload(pkg)
#         logging.debug('status: %d, value: %d', status, value)
#         if status != StatusCode.SUCCESS:
#             logging.info('TX-DATA: %s' % StatusCode[status])
#             raise McuBootDataError(mode='write', errname=StatusCode[status], errval=status)

#         logging.info('TX-DATA: Successfully Send %d Bytes', len(data))
#         return start

class UsbProtocolMixin(ProtocolMixin):
    # def __init__(self):
    #     self._pg_func = None
    #     self._pg_start = 0
    #     self._pg_end = 100
    #     self._abort = False
    #     super().__init__(self)
    _pg_func = None
    _pg_start = 0
    _pg_end = 100
    _abort = False

    def write_cmd(self, payload, timeout=1000, status_success=StatusCode.SUCCESS, **kwargs):
        if self.device is None:
            logging.info('RX-DATA: Disconnected')
            raise McuBootConnectionError('Disconnected')

        # Send USB-HID CMD OUT Report
        self.write(HID_REPORT['CMD_OUT'], payload)

        # Read USB-HID CMD IN Report
        try:
            rep_id, rx_payload = self.read(timeout)
        except:
            logging.info('RX-CMD: USB Disconnected')
            raise McuBootTimeOutError('USB Disconnected')

        # log RX raw command data
        logging.debug('RX-CMD [%02d]: %s', len(rx_payload), atos(rx_payload))
        self.last_cmd_response = rx_payload

        # Parse and validate status flag
        status, value = self.parse_response_payload(rx_payload)
        logging.debug('status: %#x, value: %#x', status, value)
        if status != status_success:
            if StatusCode.is_valid(status):
                logging.info('RX-CMD: %s', StatusCode[status])
                raise McuBootCommandError(errname=StatusCode[status], errval=status)
            else:
                logging.info('RX-CMD: Unknown Error %d', status)
                raise McuBootCommandError(errval=status)
        
        return value

    def read_data(self, length, timeout=1000):
        n = 0
        data = bytearray()
        pg_dt = float(self._pg_end - self._pg_start) / length
        # self._abort = False

        if self.device is None:
            logging.info('RX-DATA: Disconnected')
            raise McuBootConnectionError('Disconnected')

        while n < length:
            # Read USB-HID DATA IN Report
            try:
                rep_id, rx_payload = self.read(timeout) # note: The length of rx_payload is not necessarily 32 bits
            except:
                logging.info('RX-DATA: USB Disconnected')
                raise McuBootTimeOutError('USB Disconnected')

            # if rep_id != HID_REPORT['DATA_IN']:
            #     status, value = self.parse_response_payload(rx_payload)
            #     logging.debug('status: %#x, value: %#x', status, value)
            #     if StatusCode.is_valid(status):
            #         logging.info('RX-DATA: %s' % StatusCode.desc(status))
            #         raise McuBootDataError(mode='read', errname=StatusCode.desc(status), errval=status)
            #     else:
            #         logging.info('RX-DATA: Unknown Error %d' % status)
            #         raise McuBootDataError(mode='read', errval=status)

            data.extend(rx_payload)
            n += len(rx_payload)

            if self._pg_func:
                self._pg_func(self._pg_start + int(n * pg_dt))

            # if self._abort:
            #     logging.info('Read Aborted By User')
            #     return

        # Read USB-HID CMD IN Report
        try:
            rep_id, rx_payload = self.read(timeout)
        except:
            logging.info('RX-DATA: USB Disconnected')
            raise McuBootTimeOutError('USB Disconnected')
        
        self.last_cmd_response = rx_payload

        # Parse and validate status flag
        status, value = self.parse_response_payload(rx_payload)
        logging.debug('status: %#x, value: %#x', status, value)
        if status != StatusCode.SUCCESS:
            if StatusCode.is_valid(status):
                logging.info('RX-DATA: %s' % StatusCode.desc(status))
                raise McuBootDataError(mode='read', errname=StatusCode.desc(status), errval=status)
            else:
                logging.info('RX-DATA: Unknown Error %d' % status)
                raise McuBootDataError(mode='read', errval=status)
        logging.info('RX-DATA: Successfully Received %d Bytes', len(data))
        return data

    def write_data(self, data, max_packet_size=0x20):
        n = len(data)
        start = 0
        pg_dt = float(self._pg_end - self._pg_start) / n
        # self._abort = False

        if self.device is None:
            logging.info('TX-DATA: Disconnected')
            raise McuBootConnectionError('Disconnected')

        while n > 0:
            length = 0x20
            if n < length:
                length = n
            payload = data[start:start + length]

            # send USB-HID command OUT report
            self.write(HID_REPORT['DATA_OUT'], payload)

            n -= length
            start += length

            if self._pg_func:
                self._pg_func(self._pg_start + int(start * pg_dt))

            # if self._abort:
            #     logging.info('Write Aborted By User')
            #     return
        try:
            rep_id, rx_payload = self.read()
        except:
            logging.info('TX-DATA: USB Disconnected')
            raise McuBootTimeOutError('USB Disconnected')

        self.last_cmd_response = rx_payload

        # Parse and validate status flag
        status, value = self.parse_response_payload(rx_payload)
        logging.debug('status: %#x, value: %#x', status, value)
        if status != StatusCode.SUCCESS:
                logging.info('TX-DATA: %s' % StatusCode[status])
                raise McuBootDataError(mode='write', errname=StatusCode[status], errval=status)

        logging.info('TX-DATA: Successfully Send %d Bytes', len(data))

        return start

    def set_handler(self, progressbar, start_val=0, end_val=100):
        self._pg_func = progressbar
        self._pg_start = start_val
        self._pg_end = end_val

    def abort(self):
        self._abort = True

# class UsbProtocol(Protocol):
#     def __init__(self, interface):
#         self._pg_func = None
#         self._pg_start = 0
#         self._pg_end = 100
#         self._abort = False
#         super().__init__(interface)

#     def write_cmd(self, payload, timeout=1000, **kwargs):
#         # Send USB-HID CMD OUT Report
#         self._api.write(HID_REPORT['CMD_OUT'], payload)

#         # Read USB-HID CMD IN Report
#         try:
#             rep_id, rx_payload = self._api.read(timeout)
#         except:
#             logging.info('RX-CMD: USB Disconnected')
#             raise McuBootTimeOutError('USB Disconnected')

#         # log RX raw command data
#         logging.debug('RX-CMD [%02d]: %s', len(rx_payload), atos(rx_payload))
#         # Parse and validate status flag
#         status, value = self.parse_response_payload(rx_payload)
#         if status != StatusCode.SUCCESS:
#             if StatusCode.is_valid(status):
#                 logging.info('RX-CMD: %s', StatusCode[status])
#                 raise McuBootCommandError(errname=StatusCode[status], errval=status)
#             else:
#                 logging.info('RX-CMD: Unknown Error %d', status)
#                 raise McuBootCommandError(errval=status)
        
#         return value

#     def read_data(self, length, timeout=1000):
#         n = 0
#         data = bytearray()
#         pg_dt = float(self._pg_end - self._pg_start) / length
#         # self._abort = False

#         if not (self._api or self._uart_dev or self._spi_dev):
#             logging.info('RX-DATA: Disconnected')
#             raise McuBootConnectionError('Disconnected')

#         while n < length:
#             # Read USB-HID DATA IN Report
#             try:
#                 rep_id, rx_payload = self._api.read(timeout)
#             except:
#                 logging.info('RX-DATA: USB Disconnected')
#                 raise McuBootTimeOutError('USB Disconnected')

#             status, value = self.parse_response_payload(rx_payload)
#             if rep_id != HID_REPORT['DATA_IN']:
#                 if StatusCode.is_valid(status):
#                     logging.info('RX-DATA: %s' % StatusCode.desc(status))
#                     raise McuBootDataError(mode='read', errname=StatusCode.desc(status), errval=status)
#                 else:
#                     logging.info('RX-DATA: Unknown Error %d' % status)
#                     raise McuBootDataError(mode='read', errval=status)

#             data.extend(rx_payload)
#             n += len(rx_payload)

#             if self._pg_func:
#                 self._pg_func(self._pg_start + int(n * pg_dt))

#             # if self._abort:
#             #     logging.info('Read Aborted By User')
#             #     return

#         # Read USB-HID CMD IN Report
#         try:
#             rep_id, rx_payload = self._api.read(timeout)
#         except:
#             logging.info('RX-DATA: USB Disconnected')
#             raise McuBootTimeOutError('USB Disconnected')

#         # Parse and validate status flag
#         status, value = self.parse_response_payload(rx_payload)
#         if status != StatusCode.SUCCESS:
#             if StatusCode.is_valid(status):
#                 logging.info('RX-DATA: %s' % StatusCode.desc(status))
#                 raise McuBootDataError(mode='read', errname=StatusCode.desc(status), errval=status)
#             else:
#                 logging.info('RX-DATA: Unknown Error %d' % status)
#                 raise McuBootDataError(mode='read', errval=status)
#         logging.info('RX-DATA: Successfully Received %d Bytes', len(data))
#         return data

#     def write_data(self, data, max_packet_size=0x20):
#         n = len(data)
#         start = 0
#         pg_dt = float(self._pg_end - self._pg_start) / n
#         # self._abort = False

#         if self._api is None and self._uart_dev is None:
#             logging.info('TX-DATA: Disconnected')
#             raise McuBootConnectionError('Disconnected')

#         while n > 0:
#             length = 0x20
#             if n < length:
#                 length = n
#             payload = data[start:start + length]

#             # send USB-HID command OUT report
#             self._api.write(HID_REPORT['DATA_OUT'], payload)

#             n -= length
#             start += length

#             if self._pg_func:
#                 self._pg_func(self._pg_start + int(start * pg_dt))

#             # if self._abort:
#             #     logging.info('Write Aborted By User')
#             #     return
#         try:
#             rep_id, rx_payload = self._api.read()
#         except:
#             logging.info('TX-DATA: USB Disconnected')
#             raise McuBootTimeOutError('USB Disconnected')

#         # Parse and validate status flag
#         status, value = self.parse_response_payload(rx_payload)
#         if status != StatusCode.SUCCESS:
#                 logging.info('TX-DATA: %s' % StatusCode[status])
#                 raise McuBootDataError(mode='write', errname=StatusCode[status], errval=status)

#         logging.info('TX-DATA: Successfully Send %d Bytes', len(data))

#         return start

#     def set_handler(self, progressbar, start_val=0, end_val=100):
#         self._pg_func = progressbar
#         self._pg_start = start_val
#         self._pg_end = end_val

#     def abort(self):
#         self._abort = True
HID_REPORT = {
    # KBoot USB HID Reports.
    'CMD_OUT': 0x01,
    'CMD_IN': 0x03,
    'DATA_OUT': 0x02,
    'DATA_IN': 0x04
}

class FPType(int, Enum):
    # KBoot Framing Packet Type.
    ACK = 0xA1
    NACK = 0xA2
    ABORT = 0xA3
    CMD = 0xA4
    DATA = 0xA5
    PING = 0xA6
    PINGR = 0xA7


