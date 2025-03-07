# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

import os
import logging
import collections
from time import time
from struct import pack, unpack_from
from .tool import atos
from .protocol import UsbProtocolMixin

#os.environ['PYUSB_DEBUG'] = 'debug'
#os.environ['PYUSB_LOG_FILENAME'] = 'usb.log'


########################################################################################################################
# USB HID Interface Base Class
########################################################################################################################
class RawHidBase(object):

    def __init__(self):
        self.vid = 0
        self.pid = 0
        self.path = ''
        self.desc = ''
        self.vendor_name = ""
        self.product_name = ""

    def _encode_packet(self, report_id, data, pkglen=36):
        raw_data = pack('<BBH', report_id, 0x00, len(data))
        raw_data += data
        raw_data += bytes([0x00]*(pkglen - len(raw_data)))
        return raw_data

    def _decode_packet(self, raw_data):
        report_id, _, plen = unpack_from('<BBH', raw_data)
        data = raw_data[4:4 + plen]
        return report_id, data

    def open(self):
        raise NotImplementedError()

    def close(self):
        raise NotImplementedError()

    def info(self):
        return "{0:s} (0x{1:04X}, 0x{2:04X}) @ {3}".format(self.desc, self.vid, self.pid, self.path)

    def write(self, id, data, size):
        raise NotImplementedError()

    def read(self, timeout):
        raise NotImplementedError()


########################################################################################################################
# USB Interface Classes
########################################################################################################################
if os.name == "nt":
    try:
        import pywinusb.hid as hid
    except:
        raise Exception("PyWinUSB is required on a Windows Machine")


    class RawHID(RawHidBase, UsbProtocolMixin):
        """
        This class provides basic functions to access
        a USB HID device using pywinusb:
            - write/read an endpoint
        """
        def __init__(self):
            super().__init__()
            # Vendor page and usage_id = 2
            self.report = []
            # deque used here instead of synchronized Queue
            # since read speeds are ~10-30% faster and are
            # comparable to a based list implementation.
            self.rcv_data = collections.deque()
            self.device = None
            return

        # handler called when a report is received
        def __rx_handler(self, data):
            # logging.debug("rcv: %s", data[1:])
            self.rcv_data.append(data)

        def open(self):
            """ open the interface """
            logging.debug("Opening USB interface")
            self.device.set_raw_data_handler(self.__rx_handler)
            self.device.open(shared=False)

        def close(self):
            """ close the interface """
            logging.debug("Closing USB interface")
            self.device.close()

        def write(self, id, data, size=None, locate=None):
            """
            write data on the OUT endpoint associated to the HID interface

            """
            if size is None:
                size = self.report[id - 1]._HidReport__raw_report_size

            rawdata = self._encode_packet(id, data, size)
            if locate is None:
                logging.debug('USB-OUT[%d]: %s', size, atos(rawdata))
            else:
                logging.debug('USB-OUT[%d][0x%X]: %s', size, locate, atos(rawdata))
            self.report[id - 1].send(rawdata)

        def read(self, timeout=2000, locate=None):
            """
            Read data on the IN endpoint associated to the HID interface
            :param timeout:
            """
            start = time()
            while len(self.rcv_data) == 0:
                if ((time() - start) * 1000) > timeout:
                    raise Exception("Read timed out")
            rawdata = self.rcv_data.popleft()
            if locate is None:
                logging.debug('USB-IN[%d]: %s', len(rawdata), atos(rawdata))
            else:
                logging.debug('USB-IN[%d][0x%X]: %s', len(rawdata), locate, atos(rawdata))
            return self._decode_packet(bytes(rawdata))
            # return bytes(rawdata)

        @staticmethod
        def enumerate(vid=None, pid=None, path=None):
            """
            returns all the connected devices which matches PyWinUSB.vid/PyWinUSB.pid.
            returns an array of PyWinUSB (Interface) objects
            :param vid:
            :param pid:
            """
            all_devices = hid.find_all_hid_devices()

            # find devices with good vid/pid
            all_kboot_devices = []
            for d in all_devices:
                if d.vendor_id == vid and d.product_id == pid:
                    all_kboot_devices.append(d)
                elif path:  # serach by path, no need for vid, pid
                    all_kboot_devices.append(d)
                elif pid is None and d.vendor_id == vid:
                    all_kboot_devices.append(d)
                elif vid is None and d.product_id == pid:
                    all_kboot_devices.append(d)
            if not all_kboot_devices:
                logging.debug('No device connected(vid={}, pid={}), please check'
                    '"vid", "pid", "device_path"'.format(vid or 'None', pid or 'None'))
                return all_kboot_devices

            targets = []
            for dev in all_kboot_devices:
                try:
                    dev.open(shared=False)
                    report = dev.find_output_reports()
                    dev.close()
                    # Specify additional path to search.
                    if path is not None and path != dev.device_path.split('#')[-2]:
                            continue
                    if report:
                        new_target = RawHID()
                        new_target.report = report
                        new_target.vendor_name = dev.vendor_name
                        new_target.product_name = dev.product_name
                        new_target.desc = dev.vendor_name[:-1]
                        new_target.vid = dev.vendor_id
                        new_target.pid = dev.product_id
                        new_target.path = dev.device_path.split('#')[-2]    # Actually the device id, which is basically equivalent to dev.instance_id
                        new_target.device = dev
                        new_target.device.set_raw_data_handler(new_target.__rx_handler)
                        targets.append(new_target)
                except Exception as e:
                    logging.error("Receiving Exception: %s", e)
                    dev.close()

            return targets


else:
    try:
        import usb.core
        import usb.util
    except:
        raise Exception("PyUSB is required on a Linux Machine")

    class RawHID(RawHidBase, UsbProtocolMixin):
        """
        This class provides basic functions to access
        a USB HID device using pyusb:
            - write/read an endpoint
        """

        vid = 0
        pid = 0
        intf_number = 0

        def __init__(self):
            super().__init__()
            self.ep_out = None
            self.ep_in = None
            self.device = None
            self.closed = False

        def open(self):
            """ open the interface """
            logging.debug("Opening USB interface")

        def close(self):
            """ close the interface """
            logging.debug("Close USB Interface")
            self.closed = True
            try:
                if self.device:
                    usb.util.dispose_resources(self.device)
            except:
                pass

        def write(self, id, data, size=36, locate=None):
            """
            write data on the OUT endpoint associated to the HID interface
            """
            rawdata = self._encode_packet(id, data, size)
            if locate is None:
                logging.debug('USB-OUT[%d]: %s', size, atos(rawdata))
            else:
                logging.debug('USB-OUT[%d][0x%X]: %s', size, locate, atos(rawdata))

            if self.ep_out:
                self.ep_out.write(rawdata)
            else:
                bmRequestType = 0x21       #Host to device request of type Class of Recipient Interface
                bmRequest = 0x09           #Set_REPORT (HID class-specific request for transferring data over EP0)
                wValue = 0x200             #Issuing an OUT report
                wIndex = self.intf_number  #Interface number for HID
                self.device.ctrl_transfer(bmRequestType, bmRequest, wValue + id, wIndex, rawdata)

        def read(self, timeout=1000, locate=None):
            """
            read data on the IN endpoint associated to the HID interface
            """
            #rawdata = self.ep_in.read(self.ep_in.wMaxPacketSize, timeout)
            rawdata = self.ep_in.read(36, timeout)
            if locate is None:
                logging.debug('USB-IN[%d]: %s', len(rawdata), atos(rawdata))
            else:
                logging.debug('USB-IN[%d][0x%X]: %s', len(rawdata), locate, atos(rawdata))
            # logging.debug('USB-IN [0x]: %s', atos(rawdata))
            return self._decode_packet(rawdata)

        def info(self):
            if isinstance(self.path, collections.Sequence):
                path = 'Bus {p[0]:03d} Address {p[1]:03d}'.format(p=self.path)
            else:
                path = self.path
            return "{0:s} (0x{1:04X}, 0x{2:04X}) @ {3}".format(self.desc, self.vid, self.pid, path)

        @staticmethod
        def enumerate(vid=None, pid=None, path=None):
            """
            returns all the connected devices which matches PyUSB.vid/PyUSB.pid.
            returns an array of PyUSB (Interface) objects
            :param vid: Device vid
            :param pid: Device pid
            :param path: a string or sequence to represent device path, like "BUS,ADDRESS" or (0,5).(BUS 000 ADDRESS 005)
            """
            # find all devices matching the vid/pid specified

            if vid and pid:
                all_devices = usb.core.find(find_all=True, idVendor=vid, idProduct=pid)
            elif path:  # serach by path, no need for vid, pid
                all_devices = usb.core.find(find_all=True)
            elif pid is None and vid:
                all_devices = usb.core.find(find_all=True, idVendor=vid)
            elif vid is None and pid:
                all_devices = usb.core.find(find_all=True, idProduct=pid)

            if not all_devices:
                logging.debug('No device connected(vid={}, pid={}), please check'
                    '"vid", "pid", "device_path"'.format(vid or 'None', pid or 'None'))
                return []

            targets = []

            # iterate on all devices found
            for dev in all_devices:
                # Specify additional path to search.
                if path is not None:
                    if isinstance(path, str):
                        bus, address = (int(v) for v in path.split(','))
                    else:
                        try:
                            bus, address = path
                        except ValueError as e:
                            raise ValueError('device id has' + e)
                    if not (int(bus) == dev.bus and int(address) == dev.address):
                        continue

                interface = None
                interface_number = -1

                # get active config
                config = dev.get_active_configuration()

                # iterate on all interfaces:
                for interface in config:
                    if interface.bInterfaceClass == 0x03: # HID Interface
                        interface_number = interface.bInterfaceNumber
                        break

                if interface is None or interface_number == -1:
                    continue

                try:
                    if dev.is_kernel_driver_active(interface_number):
                        dev.detach_kernel_driver(interface_number)
                except Exception as e:
                    print(str(e))

                try:
                    dev.set_configuration()
                    dev.reset()
                except usb.core.USBError as e:
                    print("Cannot set configuration the device: %s" % str(e))

                ep_in, ep_out = None, None
                for ep in interface:
                    if ep.bEndpointAddress & 0x80:
                        ep_in = ep
                    else:
                        ep_out = ep

                if usb.__version__ == '1.0.0b1':
                    vendor_name = usb.util.get_string(dev, 64, 1)
                    product_name = usb.util.get_string(dev, 64, 2)
                else:
                    vendor_name = usb.util.get_string(dev, 1)
                    product_name = usb.util.get_string(dev, 2)

                if not ep_in:
                    logging.error('Endpoints not found')
                    return None

                new_target = RawHID()
                new_target.ep_in = ep_in
                new_target.ep_out = ep_out
                new_target.device = dev
                new_target.vid = dev.idVendor
                new_target.pid = dev.idProduct
                new_target.intf_number = interface_number
                new_target.vendor_name = vendor_name
                new_target.product_name = product_name
                new_target.desc = product_name
                new_target.path = (dev.bus, dev.address)
                targets.append(new_target)

            return targets



