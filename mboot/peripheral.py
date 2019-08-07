import serial.tools.list_ports
import pyftdi

from .usb import RawHID
from .exception import McuBootGenericError, McuBootConnectionError

DEVICES = {
    # NAME   | VID   | PID
    'MKL27': (0x15A2, 0x0073),
    'LPC55': (0x1FC9, 0x0021),
    'K82F' : (0x15A2, 0x0073),
    # '232h' : (0x403,0x6014),
    'KE16Z': (0x0D28, 0x0204),  # uart
    'FPGA' : (0x1A86, 0x7523)   # uart
}

FTDI = {
    '232'       : (0x0403, 0x6001),
    '232r'      : (0x0403, 0x6001),
    '232h'      : (0x0403, 0x6014),
    '2232'      : (0x0403, 0x6010),
    '2232d'     : (0x0403, 0x6010),
    '2232h'     : (0x0403, 0x6010),
    '4232'      : (0x0403, 0x6011),
    '4232h'     : (0x0403, 0x6011),
    '230x'      : (0x0403, 0x6015),
    'ft232'     : (0x0403, 0x6001),
    'ft232r'    : (0x0403, 0x6001),
    'ft232h'    : (0x0403, 0x6014),
    'ft2232'    : (0x0403, 0x6010),
    'ft2232d'   : (0x0403, 0x6010),
    'ft2232h'   : (0x0403, 0x6010),
    'ft4232'    : (0x0403, 0x6011),
    'ft4232h'   : (0x0403, 0x6011),
    'ft230x'    : (0x0403, 0x6015)
}

peripheral_speed = {
    'usb'   : 12000000,
    'uart'  : 57600,    # Minimum baud rate 1200
    'i2c'   : 100000,
    'spi'   : 1000000,  # The minimum speed is about 3000, otherwise the underlying pyftdi will report an error.
    'can'   : 500
}

def parse_port(peripheral, arg):
    port = arg.lower()
    if port.startswith('com') or port.startswith('/dev/'):
        if not peripheral.lower() == 'uart':
             raise('Uart port setting error. (port = {})'.format(arg))
    elif len(port.split(':')) == 2:
        str_list = port.split(':')
        port = (int(str_list[0],0), int(str_list[1], 0))
        # port = tuple(port.split(':'))
    elif len(port.split(',')) == 2:
        str_list = port.split(',')
        port = (int(str_list[0],0), int(str_list[1], 0))
    elif len(port.split()) == 2:
        str_list = port.split()
        port = (int(str_list[0],0), int(str_list[1], 0))
    else:
        raise('Parse port fail. (port = {})'.format(arg))
    return port

def parse_peripheral(peripheral, args):
    port = None
    product_name = peripheral
    speed = peripheral_speed[peripheral.lower()]
    # May enter a str instead of a list
    if isinstance(args, str):
        args_len = 1
    else:
        args_len = len(args)

    if args_len == 2:
        port, speed = args
        port = parse_port(peripheral, port)
    elif args_len == 1:
        if args[0].isdigit():
            speed = int(args[0], 0)
        else:
            port = args[0]
            port = parse_port(peripheral, port)
    elif args_len > 2:
        raise('peripheral length error. (peripheral = {})'.format(args))
    
    if port == None:
        scan_func = globals().get('scan_'+peripheral.lower(), None)
        if scan_func:
            product_name, port = scan_func()

    if isinstance(port, str):
        info = ' DEVICE: {0:s} ({1:s}) {2:d}'.format(product_name, port, speed)
    else:   # tuple or list
        info = ' DEVICE: {0:s} (0x{p[0]:04X}, 0x{p[1]:04X}) {1:d}'.format(product_name, speed, p=port)
    print(info)
    return port, speed

def scan_usb():
    devices = []
    for value in set(DEVICES.values()):
        # print(name, value[0], value[1])
        devices += RawHID.enumerate(value[0], value[1])
    if not devices:
        raise McuBootConnectionError("\n - Target not detected !")
    index = 0
    if len(devices) > 1:
        for i, device in enumerate(devices, 0):
            print(' {0:d}) {1:s}'.format(i, device.info()))
        c = input('\n Select: ')
        index = int(c, 10)
    product_name = devices[index].product_name
    vid_pid = (devices[index].vid, devices[index].pid)
    for device in devices:
        device.close()
    return product_name, vid_pid

def scan_uart():
    all_devices = serial.tools.list_ports.comports()
    device_list = [device for device in all_devices if device.vid and device.pid]

    possible_device = []
    for device in device_list:
        for vid_pid in set(DEVICES.values()):
            if device.vid == vid_pid[0] and device.pid == vid_pid[1]:
                possible_device.append(device)
                break
    if not possible_device:
        raise McuBootGenericError('\n - Automatic device search failed, please fill in the details')
    index = 0
    if len(possible_device) > 1:
        for i, device in enumerate(possible_device, 0):
            info = ' {0:d}) {d.manufacturer:s} {d.description:s} (0x{d.vid:04X}, 0x{d.pid:04X})'.format(i, d = device)
            print(info)
        choose = input('\n Select: ')
        index = int(choose, 10)
    selected_device = possible_device[index]
    product_name = '{d.manufacturer:s} {d.description:s}'.format(
        d = selected_device).rsplit(' (', 1)[0]
    port = selected_device.device  # port or (vid, pid)
    return product_name, port

def scan_spi():
    value = set(FTDI.values())
    devices = pyftdi.usbtools.UsbTools.find_all(value)
    if not devices: # not use, UsbTools will throw an error
        raise McuBootGenericError('\n - Automatic device search failed, please fill in the details')
    index = 0
    if len(devices) > 1:
        for i, device in enumerate(devices, 0):
            info = ' {0:d}) {d[-1]:s} ({d[1]:#04X}, {d[2]:#04X})'.format(i, d = device)
            print(info)
        c = input('\n Select: ')
        index = int(c, 10)
    *vid_pid, _, _, product_name = devices[index]
    return product_name, tuple(vid_pid)

scan_i2c = scan_spi