from sys import platform
import threading

import usb.core
import usb.util
import pyftdi

from pyftdi.spi import SpiController
from pyftdi.i2c import I2cController

class SpiController(SpiController):
    def __init__(self, silent_clock=False, cs_count=4, turbo=True):
        super(SpiController, self).__init__(silent_clock, cs_count, turbo)
        self._ftdi = Ftdi()

class I2cController(I2cController):
    def __init__(self):
        super(I2cController, self).__init__()
        self._ftdi = Ftdi()

class UsbTools(pyftdi.usbtools.UsbTools):
    """Helpers to obtain information about connected USB devices."""
    @staticmethod
    def find_all(vps, nocache=False):
        """Find all devices that match the specified vendor/product pairs.

           :param vps: a sequence of 2-tuple (vid, pid) pairs
           :type vps: tuple(int, int)
           :param bool nocache: bypass cache to re-enumerate USB devices on
                                the host
           :return: a list of 5-tuple (vid, pid, sernum, iface, description)
                    device descriptors
           :rtype: list(tuple(int,int,str,int,str))
        """
        devs = []
        for v, p in vps:
            devs.extend(UsbTools._find_devices(v, p, nocache))
        # print(devs)
        devices = []
        for dev in devs:
            ifcount = max([cfg.bNumInterfaces for cfg in dev])
            sernum = UsbTools.get_string(dev, dev.iSerialNumber) or (dev.bus, dev.address)
            description = UsbTools.get_string(dev, dev.iProduct)
            devices.append((dev.idVendor, dev.idProduct, sernum, ifcount,
                         description))
        return devices

    @classmethod
    def _find_devices(cls, vendor, product, nocache=False):
        """Find a USB device and return it.

           This code re-implements the usb.core.find() method using a local
           cache to avoid calling several times the underlying LibUSB and the
           system USB calls to enumerate the available USB devices. As these
           calls are time-hungry (about 1 second/call), the enumerated devices
           are cached. It consumes a bit more memory but dramatically improves
           start-up time.
           Hopefully, this kludge is temporary and replaced with a better
           implementation from PyUSB at some point.

           :param int vendor: USB vendor id
           :param int product: USB product id
           :param bool nocache: bypass cache to re-enumerate USB devices on
                                the host
           :return: a set of USB device matching the vendor/product identifier
                    pair
           :rtype: set(usb.core.Device)

        """
        cls.Lock.acquire()
        try:
            backend = None
            candidates = ('libusb1', 'libusb10', 'libusb0', 'libusb01',
                          'openusb')
            um = __import__('usb.backend', globals(), locals(),
                            candidates, 0)
            for c in candidates:
                try:
                    m = getattr(um, c)
                except AttributeError:
                    continue
                backend = m.get_backend()
                if backend is not None:
                    break
            else:
                raise ValueError('No backend available')
            vp = (vendor, product)
            if nocache or (vp not in cls.UsbDevices):
                # not freed until Python runtime completion
                # enumerate_devices returns a generator, so back up the
                # generated device into a list. To save memory, we only
                # back up the supported devices
                devs = set()
                vpdict = {}
                vpdict.setdefault(vendor, [])
                vpdict[vendor].append(product)
                for dev in backend.enumerate_devices():
                    device = usb.core.Device(dev, backend)
                    if device.idVendor in vpdict:
                        products = vpdict[device.idVendor]
                        if products and (device.idProduct not in products):
                            continue
                        devs.add(device)
                # if platform == 'win32':
                    # ugly kludge for a boring OS:
                    # on Windows, the USB stack may enumerate the very same
                    # devices several times: a real device with N interface
                    # appears also as N device with as single interface.
                    # We only keep the "device" that declares the most
                    # interface count and discard the "virtual" ones.
                filtered_devs = dict()
                for dev in devs:
                    vid = dev.idVendor
                    pid = dev.idProduct
                    ifc = max([cfg.bNumInterfaces for cfg in dev])
                    sn = UsbTools.get_string(dev, dev.iSerialNumber)
                    k = (vid, pid, sn, dev.bus, dev.address)
                    if k not in filtered_devs:
                        filtered_devs[k] = dev
                    else:
                        fdev = filtered_devs[k]
                        fifc = max([cfg.bNumInterfaces for cfg in fdev])
                        if fifc < ifc:
                            filtered_devs[k] = dev
                devs = [filtered_devs[k] for k in sorted(filtered_devs.keys())]
                # devs = list(filtered_devs.values())
                    
                cls.UsbDevices[vp] = devs
            return cls.UsbDevices[vp]
        finally:
            cls.Lock.release()

# Monkey patch
pyftdi.usbtools.UsbTools = UsbTools

class Ftdi(pyftdi.ftdi.Ftdi):
    @staticmethod
    def find_all(vps, nocache=False):
        """Find all devices that match the vendor/product pairs of the vps
           list.

           :param vps: a sequence of 2-tuple (vid, pid) pairs
           :type vps: tuple(int, int)
           :param bool nocache: bypass cache to re-enumerate USB devices on
                                the host
           :return: a list of 5-tuple (vid, pid, sernum, iface, description)
                    device descriptors
           :rtype: list(tuple(int,int,str,int,str))
        """
        return UsbTools.find_all(vps, nocache)

    def open(self, vendor, product, index=0, serial=None, interface=1):
        """Open a new interface to the specified FTDI device.

           If several FTDI devices of the same kind (vid, pid) are connected
           to the host, either index or serial argument should be used to
           discriminate the FTDI device.

           index argument is not a reliable solution as the host may enumerate
           the USB device in random order. serial argument is more reliable
           selector and should always be prefered.

           Some FTDI devices support several interfaces/ports (such as FT2232H
           and FT4232H). The interface argument selects the FTDI port to use,
           starting from 1 (not 0).

           :param int vendor: USB vendor id
           :param int product: USB product id
           :param int index: optional selector, specified the n-th matching
                             FTDI enumerated USB device on the host
           :param str serial: optional selector, specified the FTDI device
                              by its serial number
           :param str interface: FTDI interface/port
        """
        self.usb_dev = UsbTools.get_device(vendor, product, index, serial)
        try:
            self.usb_dev.set_configuration()
        except usb.core.USBError:
            pass
        # detect invalid interface as early as possible
        config = self.usb_dev.get_active_configuration()
        if interface > config.bNumInterfaces:
            raise FtdiError('No such FTDI port: %d' % interface)
        self._set_interface(config, interface)
        self.max_packet_size = self._get_max_packet_size()
        # Drain input buffer
        self.purge_buffers()
        self._reset_device()
        self.set_latency_timer(self.LATENCY_MIN)

