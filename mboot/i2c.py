import time
import struct
import logging

from .tool import atos
from .protocol import FPType, UartProtocolMixin
from .exception import McuBootDataError, McuBootTimeOutError
from .enums import StatusCode
from .ftditool import I2cController

class I2C(UartProtocolMixin):
    def __init__(self, freq):
        self.freq = int(freq, 0) if isinstance(freq, str) else freq
        self.controller = None
        self.slave = None

    def open(self, vid=None, pid=None, index=1, slave_address=0x10):
        """ open the interface """
        self.controller = I2cController()

        # [URL Scheme — PyFtdi documentation](https://eblot.github.io/pyftdi/urlscheme.html#url-scheme)
        # # spi.configure('ftdi:///1')
        # url = 'ftdi://ftdi:{}/1'.format(target)
        url = 'ftdi://{}:{}:{}/1'.format(vid or '', pid or '', index)
        self.controller.configure(url, frequency=self.freq)
        # print('frequency', self.controller.frequency)
        self.slave = self.controller.get_port(slave_address)
        logging.debug("Opening I2C interface")

    def close(self):
        """ close the interface """
        self.controller.terminate()
        logging.debug("Close I2C Interface")
    
    def read(self, packet_type, rx_ack=False, tx_ack=True, locate=None):
        start_byte = self.find_start_byte()
        if rx_ack:
            if not self.slave.read(1)[0] == FPType.ACK:
                raise EnvironmentError
            self.find_start_byte()
        head = start_byte + self.slave.read(5).tobytes()
        logging.debug('I2C-IN-%s-HEAD[%d]: %s', packet_type.name, len(head), atos(head))
        _, _packet_type, payload_len, crc = struct.unpack('<2B2H', head) # framing packet
        if not _packet_type == packet_type:
            if _packet_type == FPType.CMD:   # Slave interrupt in read data
                pass    # Read out the rest of the command
            else:
                raise EnvironmentError
        payload = self.slave.read(payload_len).tobytes()

        if locate is None:
            logging.debug('I2C-IN-%s-PAYLOAD[%d]: %s', packet_type.name, len(payload), atos(payload))
        else:
            logging.debug('I2C-IN-%s-PAYLOAD[%d][0x%X]: %s', packet_type.name, len(payload), locate, atos(payload))

        if tx_ack:
            self._send_ack()

        return head, payload
    
    def write(self, packet_type, data, rx_ack=True, timeout=1, locate=None):
        self.slave.write(data)  # The array 'data' will changed into a list during execution.
        if locate is None:
            logging.debug('I2C-OUT-%s[%d]: %s', packet_type.name, len(data), atos(data))
        else:
            logging.debug('I2C-OUT-%s[%d][0x%X]: %s', packet_type.name, len(data), locate, atos(data))
        if rx_ack:
            self._receive_ack(timeout)

    def ping(self):
        ping = bytes(b'\x5A\xA6')
        self.slave.write(ping)
        logging.debug('I2C-OUT-PING[%d]: %s', len(ping), atos(ping))

        start_byte = self.find_start_byte()
        data = start_byte + self.slave.read(9).tobytes()
        logging.debug('I2C-OUT-PINGR[%d]: %s', len(data), atos(data))
        _, packet_type, *protocol_version, protocol_name, options, crc = struct.unpack('<6B2H', data)
        if not packet_type == FPType.PINGR:
                raise EnvironmentError
        return data

    def find_start_byte(self, timeout=1):
        '''find start byte (0x5A) of the packet
        :param timeout: timeout
        :return array of start byte
        '''
        # logging.debug('current timeout: {}'.format(timeout))
        # timeout logic
        start_time = time.perf_counter()

        # Return before time runs out
        while time.perf_counter() - start_time < timeout:
            start = self.slave.read(1).tobytes()  # return array.array
            # logging.debug('{!r} {}'.format(start, type(start)))
            if start[0] == 0x5A:
                return start

        raise McuBootTimeOutError

    def _send_ack(self):
        '''Used to send ack after read phase
        '''
        ack = bytes(b'\x5A\xA1')
        self.slave.write(ack)
        logging.debug('I2C-OUT-ACK[%d]: %s', len(ack), atos(ack))

    def _receive_ack(self, timeout):
        '''Used to receive ack after write phase
        '''
        ack = self.find_start_byte(timeout)
        ack += self.slave.read(1).tobytes()
        logging.debug('I2C-IN-ACK[2]: %s', atos(ack))
        packet_type = ack[1]
        if not packet_type == FPType.ACK:
            if packet_type == FPType.ABORT:
                raise McuBootDataError(mode='read', errname=StatusCode[0x2712])
            else:
                raise McuBootDataError('recevice ack error, packet_type={!s}(0x{:X})'
                    .format(FPType(packet_type), packet_type))

