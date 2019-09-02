import inspect
from string import printable

import bincopy

from .exception import McuBootGenericError

def size_fmt(value, use_kibibyte=True):
    """ Convert integer value to string with size mark
    :param value:
    :param use_kibibyte:
    :return:
    """
    base, suffix = [(1000., 'B'), (1024., 'iB')][use_kibibyte]
    for unit in ['B'] + [x + suffix for x in list('kMGTP')]:
        if -base < value < base:
            break
        value /= base
    return "{0:3.1f} {1:s}".format(value, unit)


def atos(data, separator=' ', fmt='02X'):
    """ Convert array of bytes to string
    :param data: Data in bytes or bytearray type
    :param separator: String separator
    :param fmt: String format
    :return string
    """
    ret = ''
    for x in data:
        if fmt == 'c' and x not in printable.encode():
            ret += '.'
            continue
        ret += ('{:'+fmt+'}').format(x)
        ret += separator
    return ret

def crc16(data, crc=0, poly=0x1021):
    '''Default calculate CRC-16/XMODEM
    width:      16
    polynomial: 0x1021
    init value: 0x0000
    xor out:    0x0000
    reflect in false
    reflect out false
    '''
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            temp = crc << 1
            if crc & 0x8000:
                temp ^= poly
            crc = temp
    return crc & 0xFFFF

def check_method_arg_number(func, args_len):
    """Check whether the method can input x arguments
    :param func: The method to check
    :param args_len: The length of arguments to be entered
    :return Result of judgment
    :rtype: bool
    """
    pass_flag = False
    ori_func = inspect.unwrap(func)
    ori_args = inspect.getfullargspec(ori_func)
    func_args_len = len(ori_args.args) if ori_args.args else 0

    # instance/class method, subtract the 'self/cls' arg
    if 'self' in ori_args.args:
        func_args_len -= 1
    
    min_func_args_len = func_args_len - len(ori_args.defaults) if ori_args.defaults else func_args_len

    if ori_args.varargs or ori_args.varkw:
        # The number of functions accepted by the function has no maximum
        if args_len >= min_func_args_len:
            pass_flag = True
    else:
        if min_func_args_len <= args_len <= func_args_len:
            pass_flag = True
    return pass_flag

def convert_arg_to_int(cmd_args):
    """Convert str to int as much as possible
    :param cmd_args: the sequence of args
    :return the sequence of args
    """
    args = []
    for arg in cmd_args:
        if isinstance(arg, str):    # Int will cause TypeError
            try:
                arg = int(arg, 0)
            except ValueError:
                pass    # Unable to convert
        args.append(arg)
    return args

def check_key(value):
    if value[0] == 'S':
        if len(value) != 10:
            # self.fail('Short key, use 16 ASCII chars !', param, ctx)
            raise ValueError('Key type error, use 16 ASCII chars, such as "S:123...8"')
        bdoor_key = [ord(k) for k in value[2:]]
    elif value[0] == 'X':
        if len(value) != 18:
            # self.fail('Short key, use 32 HEX chars !', param, ctx)
            raise ValueError('Key type error, use 32 HEX chars, such as "X:010203...08"')
        value = value[2:]
        bdoor_key = []
        try:
            for i in range(0, len(value), 2):
                bdoor_key.append(int(value[i:i+2], 16))
        except ValueError:
            # self.fail('Unsupported HEX char in Key !', param, ctx)
            raise ValueError('Unsupported HEX char in Key! ({})'.format(value))
    else:
        value_len = len(value)
        if value_len == 8:
            bdoor_key = [ord(k) for k in value[2:]]
        elif value_len == 16:
            bdoor_key = []
            try:
                for i in range(0, len(value), 2):
                    bdoor_key.append(int(value[i:i+2], 16))
            except ValueError:
                # self.fail('Unsupported HEX char in Key !', param, ctx)
                raise ValueError('Unsupported HEX char in Key! ({})'.format(value))
        else:
            raise ValueError('Key type error, Use backdoor key as "ASCII = S:123...8" or "HEX = X:010203...08"')
    return bdoor_key

def check_int(value):
    # Convert hex str to int
    # if isinstance(value, str):
    try:
        value = int(value, 0)
    except ValueError:
        # raise argparse.ArgumentTypeError("%s is an invalid positive int value" % value)
        raise ValueError("%s is an invalid positive int value" % values)
    else:
        return value

def hexdump(data, start_address=0, compress=True, length=16, sep='.'):
    """ Return string array in hex-dump format
    :param data:          {List} The data array of {Bytes}
    :param start_address: {Int}  Absolute Start Address
    :param compress:      {Bool} Compressed output (remove duplicated content, rows)
    :param length:        {Int}  Number of Bytes for row (max 16).
    :param sep:           {Char} For the text part, {sep} will be used for non ASCII char.
    """
    msg = []

    # The max line length is 16 bytes
    if length > 16:
        length = 16

    # Create header
    header = ' ADDRESS | '
    for i in range(0, length):
        header += "{:02X} ".format(i)
    header += '| '
    for i in range(0, length):
        header += "{:X}".format(i)
    msg.append(header)
    msg.append((' ' + '-' * (13 + 4 * length)))

    # Check address align
    offset = start_address % length
    address = start_address - offset
    align = True if (offset > 0) else False

    # Print flags
    prev_line = None
    print_mark = True

    # process data
    for i in range(0, len(data) + offset, length):

        hexa = ''
        if align:
            subSrc = data[0: length - offset]
        else:
            subSrc = data[i - offset: i + length - offset]
            if compress:
                # compress output string
                if subSrc == prev_line:
                    if print_mark:
                        print_mark = False
                        msg.append(' *')
                    continue
                else:
                    prev_line = subSrc
                    print_mark = True

        if align:
            hexa += '   ' * offset

        for h in range(0, len(subSrc)):
            h = subSrc[h]
            if not isinstance(h, int):
                h = ord(h)
            hexa += "{:02X} ".format(h)

        text = ''
        if align:
            text += ' ' * offset

        for c in subSrc:
            if not isinstance(c, int):
                c = ord(c)
            if 0x20 <= c < 0x7F:
                text += chr(c)
            else:
                text += sep

        msg.append((' {:08X} | {:<' + str(length * 3) + 's}| {:s}').format(address + i, hexa, text))
        align = False

    msg.append((' ' + '-' * (13 + 4 * length)))
    return '\n'.join(msg)

def read_file(filename, address=None):
    in_data = bincopy.BinFile()
    try:
        if filename.lower().endswith(('.srec', '.s19')):
            in_data.add_srec_file(filename)
            if address is None:
                address = in_data.minimum_address
        elif filename.lower().endswith(('.hex', '.ihex')):
            in_data.add_ihex_file(filename)
            if address is None:
                address = in_data.minimum_address
        else:
            in_data.add_binary_file(filename)
            if address is None:
                raise McuBootGenericError('Write a bin file to device must provide a write address.')
        data = in_data.as_binary()
    except Exception as e:
        raise Exception('Could not write to file {}:\n [{}]'.format(filename, str(e)))
    return data, address

def write_file(filename, data):
    try:
        if filename.lower().endswith(('.srec', '.s19')):
            srec = bincopy.BinFile()
            srec.add_binary(data, address)
            srec.header = 'mboot'
            with open(filename, "w") as f:
                f.write(srec.as_srec())
        elif filename.lower().endswith(('.hex', '.ihex')):
            ihex = bincopy.BinFile()
            ihex.add_binary(data, address)
            with open(filename, "w") as f:
                f.write(ihex.as_ihex())
        else:
            with open(filename, "wb") as f:
                f.write(data)
    except Exception as e:
        raise Exception('Could not write to file {}:\n [{}]'.format(filename, str(e)))

if __name__ == '__main__':
    data = bytes.fromhex('5A A4 0C 00 07 00 00 02 01 00 00 00 00 00 00 00')
    # import array
    # data = array.array('B', data)
    result = crc16(data)
    

    print('data:{}\nresult:{}'.format(data, result))
