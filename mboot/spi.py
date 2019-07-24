import logging

from pyftdi.spi import SpiController
from struct import pack, unpack
from .misc import atos
from .protocol import FPType, UartProtocolMixin
from .exception import McuBootDataError
from .enums import StatusCode

# 5A-A6-5A-A4-0C-00-4B-33-07-00-00-02-01-00-00-00-00-00-00-00
class SPI(UartProtocolMixin):
    def __init__(self, freq=1000*1000, mode=0):
        self.mode = mode
        self.freq = int(freq, 0) if isinstance(freq, str) else freq
        self.controller = None
        self.slave = None

    def open(self, vid, pid):
        """ open the interface """
        self.controller = SpiController(cs_count=4)
        
        # [URL Scheme — PyFtdi documentation](https://eblot.github.io/pyftdi/urlscheme.html#url-scheme)
        # # spi.configure('ftdi:///1')
        # url = 'ftdi://ftdi:{}/1'.format(target)
        url = 'ftdi://{}:{}/1'.format(vid, pid)
        self.controller.configure(url)
        self.slave = self.controller.get_port(cs=0, freq=self.freq, mode=self.mode)

    def close():
        """ close the interface """
        self.controller.terminate()
    
    def read(self, packet_type, rx_ack=False, tx_ack=True):
        # data = self.slave.read(length).tobytes()
        # logging.debug('SPI-IN-%s-ORIGIN[%d]: %s', packet_type.name, len(data), atos(data))
        # start_index = data.find(0x5A)

            # if not data[start_index+1] == FPType.ACK:
            #     raise EnvironmentError
        #     start_index = data.find(0x5A, start_index+2)
        # _, _packet_type, payload_len, crc = unpack_from('<2B2H', data, start_index) # framing packet
        # if not _packet_type == packet_type:
        #     raise EnvironmentError
        # head = data[start_index:start_index+6]
        # logging.debug('SPI-IN-HEAD[%d]: %s', len(head), atos(head))
        # end_index = start_index + 6 + payload_len
        # if end_index > length:
        #     data2 = self.slave.read(end_index - length).tobytes()
        #     # logging.debug('SPI-IN-%s-ORIGIN[%d]: %s', packet_type.name, len(data2), atos(data2))
        #     payload = data[start_index+6:] + data2
        # else:
        #     payload = data[start_index+6:end_index]

        start_byte = self.find_start_byte()
        if rx_ack:
            if not self.slave.read(1)[0] == FPType.ACK:
                raise EnvironmentError
            self.find_start_byte()
        head = start_byte.tobytes() + self.slave.read(5).tobytes()
        _, _packet_type, payload_len, crc = unpack('<2B2H', head) # framing packet
        logging.debug('SPI-IN-%s-HEAD[%d]: %s', packet_type.name, len(head), atos(head))
        if not _packet_type == packet_type:
            if _packet_type == FPType.CMD:   # Slave interrupt in read data
                pass    # Read out the rest of the command
            else:
                raise EnvironmentError
        payload = self.slave.read(payload_len).tobytes()

        logging.debug('SPI-IN-%s-PAYLOAD[%d]: %s', packet_type.name, len(payload), atos(payload))

        if tx_ack:
            self.send_ack()

        return head, payload
    
    def write(self, packet_type, data, rx_ack=True):
        # data = self.protocol.genPacket(packet_type, payload)
        # self.ping()
        self.slave.write(data)  # The array 'data' will changed into a list during execution.
        logging.debug('SPI-OUT-%s[%d]: %s', packet_type.name, len(data), atos(data))
        if rx_ack:
            self.receive_ack()

    def ping(self):
        ping = bytes(b'\x5A\xA6')
        self.slave.write(ping)
        logging.debug('SPI-OUT-PING[%d]: %s', len(ping), atos(ping))
        # data = self.slave.read(11).tobytes()
        # logging.debug('SPI-IN-PINGR-ORIGIN[%d]: %s', len(data), atos(data))
        # if data == b'\x00' * 11:
        #     pass    # The device has successfully handshake and does not need to repeat the handshake.
        # else:
        #     start_index = data.find(0x5A)
        #     if start_index > 1: # It is possible that the ping response will be delayed.
        #         data += self.slave.read(10).tobytes()
        #     _, packet_type, *protocol_version, protocol_name, options, crc = unpack_from('<6B2H', data, start_index)
        #     if not packet_type == FPType.PINGR:
        #         raise EnvironmentError

        start_byte = self.find_start_byte()
        data = start_byte.tobytes() + self.slave.read(9).tobytes()
        logging.debug('SPI-OUT-PINGR[%d]: %s', len(data), atos(data))
        _, packet_type, *protocol_version, protocol_name, options, crc = unpack('<6B2H', data)
        if not packet_type == FPType.PINGR:
                raise EnvironmentError
        return data

    def find_start_byte(self, timeout=5000):
        '''find start byte (0x5A) of the packet
        :param timeout: timeout
        :return array of start byte
        '''
        # Todo: add timeout logic
        while 1:
            start = self.slave.read(1)
            if start[0] == 0x5A:
                break
        return start

    def send_ack(self):
        '''Used to send ack after read phase
        '''
        ack = bytes(b'\x5A\xA1')
        self.slave.write(ack)
        logging.debug('SPI-OUT-ACK[%d]: %s', len(ack), atos(ack))

    def receive_ack(self):
        '''Used to receive ack after write phase
        '''
        # data = self.slave.read(0x50).tobytes()
        # logging.debug('SPI-IN-ORIGIN++[%d]: %s', len(data), atos(data))
        # start_index = data.find(0x5A)
        self.find_start_byte()
        packet_type = self.slave.read(1)[0]
        if not packet_type == FPType.ACK:
            if packet_type == FPType.ABORT:
                raise McuBootDataError(mode='read', errname=StatusCode[0x2712])
            else:
                raise McuBootDataError('recevice ack error, packet_type={!s}(0x{:X})'
                    .format(FPType(packet_type), packet_type))
        else:
            logging.debug('SPI-IN-ACK[2]: 5A A1')

    def _read_command_packet(self, length=20, rx_ack=True, tx_ack=False):
        data = self.slave.read(length).tobytes()
        logging.debug('SPI-IN-ORIGIN[%d]: %s', len(data), atos(data))

        start_index = data.find(0x5A)
        if rx_ack:
            if not data[start_index+1] == FPType.ACK:
                raise EnvironmentError
            cmd_index = data.find(0x5A, start_index+2)
        else:
            cmd_index = start_index
        _, packet_type, payload_len, crc = unpack_from('<2B2H', data, cmd_index) # framing packet
        if not packet_type == FPType.CMD:
            raise EnvironmentError
        head = data[cmd_index:cmd_index+6]
        # logging.debug('SPI-IN-HEAD[%d]: %s', len(head), atos(head))

        end_index = cmd_index + 6 + payload_len
        if end_index > length:
            data2 = self.slave.read(end_index - length).tobytes()
            logging.debug('SPI-IN-ORIGIN[%d]: %s', len(data2), atos(data2))
            payload = data[cmd_index+6:] + data2
        else:
            payload = data[cmd_index+6:end_index]

        logging.debug('SPI-IN-HEAD[%d]-PAYLOAD[%d]: %s%s', len(head), len(payload), atos(head), atos(payload))

        if tx_ack:
            self.send_ack()

        return payload
    
    def _read_data_packet(self, length=0x20+0x6+5, tx_ack=True):
        data = self.slave.read(length).tobytes()
        logging.debug('SPI-IN-ORIGIN[%d]: %s', len(data), atos(data))

        cmd_index = data.find(0x5A)
        _, packet_type, payload_len, crc = unpack_from('<2B2H', data, cmd_index)
        if not packet_type == FPType.DATA:
            raise EnvironmentError
        
        head = data[cmd_index:cmd_index+6]
        end_index = cmd_index + 6 + payload_len
        if end_index > length:
            data2 = self.slave.read(end_index - length).tobytes()
            logging.debug('SPI-IN-ORIGIN[%d]: %s', len(data2), atos(data2))
            payload = data[cmd_index+6:] + data2
        else:
            payload = data[cmd_index+6:end_index]

        logging.debug('SPI-IN-HEAD[%d]-PAYLOAD[%d]: %s%s', len(head), len(payload), atos(head), atos(payload))

        if tx_ack:
            self.send_ack()

        return payload
  