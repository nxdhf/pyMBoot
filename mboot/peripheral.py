import time
import serial.tools.list_ports

from .usb import RawHID
from .exception import McuBootGenericError, McuBootConnectionError
from .ftditool import UsbTools
# DEVICES = {
#     # NAME   | VID   | PID
#     'MKL27': (0x15A2, 0x0073),
#     'LPC55': (0x1FC9, 0x0021),
#     'K82F' : (0x15A2, 0x0073),
#     'KE16Z': (0x0D28, 0x0204),  # uart
#     'FPGA' : (0x1A86, 0x7523)   # uart
# }

USB_DEV = {
    #   VID | PID
    (0x15A2, None), 
    (0x1FC9, None)
}

UART_DEV = {
    (0x0D28, None)
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
        port = arg  # Case sensitive under linux
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

def parse_peripheral(peripheral, args, auto_scan=True):
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
            port = parse_port(peripheral, args[0])
    elif args_len > 2:
        raise('peripheral length error. (peripheral = {})'.format(args))

    if auto_scan:
        scan_func = globals().get('scan_'+peripheral.lower(), None)
        if scan_func:
            product_name, config = scan_func(port)
        return config, speed

    return port, speed

def scan_usb(vid_pid=None):
    devices = []
    if vid_pid is None:
        for value in USB_DEV:
            # print(name, value[0], value[1])
            devices += RawHID.enumerate(value[0], value[1])
    else:
        devices += RawHID.enumerate(vid_pid[0], vid_pid[1])
    if not devices:
        raise McuBootConnectionError("\n - Target not detected !")
    count = 1
    if len(devices) > 1:
        for i, device in enumerate(devices, 1):
            print(' {0:d}) {1:s}'.format(i, device.info()))
        c = input('\n Select: ')
        count = int(c, 10)
    select_device = devices[count-1]
    desc = select_device.desc
    # if prompt:
    #     vid_pid = (devices[count].vid, devices[count].pid, devices[count].path)
    # else:   # Manually specify which device to select when repeating vid, pid, no need to pass in again
    #     vid_pid = (devices[count].vid, devices[count].pid)
    config = (select_device.vid, select_device.pid, select_device.path)
    # for device in devices:
    #     device.close()
    print(' DEVICE: {0:s} (0x{c[0]:04X}, 0x{c[1]:04X}) @ {c[2]}'.format(desc, c=config))
    return desc, config

def scan_uart(port=None):
    for i in range(0, 9):
        all_devices = serial.tools.list_ports.comports()
        if not all_devices:
            raise McuBootGenericError('\n - Automatic device search failed, please fill in the details')
        if port is None:
            device_list = [device for device in all_devices if device.vid and device.pid]
            possible_device = []
            for device in device_list:
                for vid, pid in UART_DEV:
                    if pid is None and vid == device.vid:
                        possible_device.append(device)
                    elif vid == device.vid and pid == device.pid:
                        possible_device.append(device)
        else:
            possible_device = [device for device in all_devices if device.device == port]
        if not possible_device:
            time.sleep(0.1) # Waiting for device initialization to complete
        else:
            break
    # According to pid, vid search fails, search by serial port number
    if not possible_device:
        possible_device = all_devices

    count = 1
    if len(possible_device) > 1:
        for i, device in enumerate(possible_device, 1):
            # desc = '{d.manufacturer:s} {d.description:s}'.format(d = device).rsplit(' (', 1)[0]
            desc = '{} {}'.format(device.manufacturer or '', device.description or '').rsplit(' (', 1)[0]
            try:
                info = ' {0:d}) {1} ({d.device:s}) (0x{d.vid:04X}, 0x{d.pid:04X})'.format(i, desc, d = device)
            except TypeError:
                info = ' {0:d}) {1} ({d.device:s})'.format(i, desc, d = device)
            print(info)
        choose = input('\n Select: ')
        count = int(choose, 10)
    selected_device = possible_device[count-1]
    desc = '{d.manufacturer:s} {d.description:s}'.format(d = selected_device).rsplit(' (', 1)[0]
    port = selected_device.device  # port or (vid, pid)
    return desc, port

def scan_spi(vid_pid):
    if vid_pid is None:
        value = set(FTDI.values())
        # devices = pyftdi.usbtools.UsbTools.find_all(value)
        devices = UsbTools.find_all(value)
    else:
        devices = UsbTools.find_all([vid_pid])
    if not devices: # not use, UsbTools will throw an error
        raise McuBootGenericError('\n - Automatic device search failed, please fill in the details')
    count = 1   # used for CLI prompt
    if len(devices) == 1:
        index_list = [1]
    if len(devices) > 1:
        count_dict = {}
        index_list = []
        for i, device in enumerate(devices, 1):
            k = (device[0], device[1])
            count_dict[k] = count_dict.get(k, 1)
            index_list.append(count_dict[k])
            count_dict[k] += 1
            info = ' {0:d}) {d[4]:s} (0x{d[0]:04X}, 0x{d[1]:04X}) {d[2]}'.format(i, d = device)
            print(info)
        c = input('\n Select: ')
        count = int(c, 10)
    *vid_pid, _, _, desc = devices[count-1]
    index = index_list[count-1] # used for pyftdi URL parsing
    config = tuple(vid_pid + [index])
    return desc, config

scan_i2c = scan_spi
