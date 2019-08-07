import sys
import argparse
import mboot

import logging
from .tool import check_method_arg_number, convert_arg_to_int, check_key, check_int, hexdump, read_file
from .enums import PropertyTag
from .constant import Interface
from .memorytool import MemoryBlock
from .peripheral import parse_peripheral
from .exception import McuBootGenericError

def parse_args(parser, subparsers, command=None):
    if command is None:
        command = sys.argv[1:]
    # Divide argv by commands
    split_argv = [[]]

    if '-o' in command or '--origin' in command: # origin interface
        split_argv[-1].extend(command)
    else:
        for c in command:
            if c in subparsers.choices:
                split_argv.append([c])
            else:
                split_argv[-1].append(c)
                # print(split_argv[-1])
    # Initialize namespace
    args = argparse.Namespace()
    # Set command name, such as cmd1, cmd2..
    for c in subparsers.choices:
        setattr(args, c, None)
    # Parse each command
    parser.parse_args(split_argv[0], namespace=args)  # Without command
    # print(args)
    # print(split_argv)
    for argv in split_argv[1:]:  # Each Subcommands
        n = argparse.Namespace()
        setattr(args, argv[0], n)
        # print(args)
        # Prevents the addition of commands defined by the parent parser
        parser._parse_known_args(list(argv), namespace=n)
    return args

def info(mb, memory_id):
    nfo = mb.get_mcu_info()
    # Print MCUBoot MCU Info
    for key, value in nfo.items():
        m = " {}:".format(key)
        if isinstance(value, list):
            m += "".join(["\n  - {}".format(s) for s in value])
        else:
            m += "\n  = {}".format(value)
        print(m)
    if memory_id:
        info = mb.get_exmemory_info(memory_id)
        print(info)

def write(mb, address, filename, memory_id=0, offset=0):
    mb.get_memory_range()
    data, start_address = read_file(filename, address)
    length = len(data) - offset
    data = data[offset:]
    block = MemoryBlock(start_address, None, length)
    if memory_id:
        # Todo configure memory
        mb.flash_erase_region(start_address, length, memory_id)
    else:
        if mb.is_in_flash(block):   # erase first if block in the flash area
            mb.flash_erase_region(block.start, block.length)
        elif mb.is_in_memory(block):
            pass
        else:
            raise McuBootGenericError('MemoryRangeInvalid, please check the address range.')
        start = mb.get_property(PropertyTag.RAM_START_ADDRESS)
    mb.write_memory(start_address, data, memory_id)

def read(mb, address, length, filename=None, memory_id=0, compress=False):
    mb.get_memory_range()
    block = MemoryBlock(address, None, length)
    if memory_id:
        # Todo configure memory
        pass
    else:
        if not (mb.is_in_flash(block) or mb.is_in_memory(block)):
            raise McuBootGenericError('MemoryRangeInvalid, please check the address range.')
    data = mb.read_memory(address, length, filename, memory_id)
    print('\n', hexdump(data, address, compress))

# def handle_exception(func):
#     def decorate(func):
#         try:
#             func()
#         except McuBootGenericError as e:
#             err_msg = '\n' + traceback.format_exc() if ctx.obj['DEBUG'] else ' ERROR: {}'.format(str(e))

def fill(mb, address, byte_count, pattern, unit):
    mb.get_memory_range()
    block = MemoryBlock(address, None, byte_count*8)
    if mb.is_in_flash(block):
        mb.flash_erase_region(block.start, block.length)
    elif mb.is_in_memory(block):
        pass
    else:
        raise McuBootGenericError('MemoryRangeInvalid, please check the address range.')
    mb.fill_memory(address, byte_count, pattern, unit)

def erase(mb, address, length, memory_id=0, erase_all = False):
    if erase_all:
        # Get available commands
        commands = mb.get_property(mboot.PropertyTag.AVAILABLE_COMMANDS)
        # Call KBoot flash erase all function
        if mboot.is_command_available(mboot.CommandTag.FLASH_ERASE_ALL_UNSECURE, commands):
            mb.flash_erase_all_unsecure()
        elif mboot.is_command_available(mboot.CommandTag.FLASH_ERASE_ALL, commands):
            mb.flash_erase_all()
        else:
            raise McuBootGenericError('Not Supported "flash_erase_all_unsecure/flash_erase_all" Command')
    else:
        # Call KBoot flash erase region function
        mb.flash_erase_region(address, length, memory_id)

def unlock(mb, key=None):
    if key is None:
        # Call KBoot flash erase all and unsecure function
        mb.flash_erase_all_unsecure()
    else:
        # Call KBoot flash security disable function
        mb.flash_security_disable(key)

class MBootHelpFormatter(argparse.ArgumentDefaultsHelpFormatter):
    def __init__(self, prog, *args, **kwargs):
        super(MBootHelpFormatter, self).__init__(prog, max_help_position=35, *args, **kwargs)

    def add_usage(self, usage, actions, groups, prefix=None):
        if prefix is None:
            prefix = 'Usage: '
        return super(MBootHelpFormatter, self).add_usage(
            usage, actions, groups, prefix)

    def _format_args(self, action, default_metavar):
        get_metavar = self._metavar_formatter(action, default_metavar)
        if action.nargs is None:
            result = '%s' % get_metavar(1)
        elif action.nargs == argparse.OPTIONAL:
            result = '[%s]' % get_metavar(1)
        elif action.nargs == argparse.ZERO_OR_MORE:
            if action.metavar is None:
                result = '[%s [%s ...]]' % get_metavar(2)
            else:
                if isinstance(action.metavar, str):
                    metavar_len = 1
                else:
                    metavar_len = len(action.metavar)
                if metavar_len == 1:
                    result = '[%s]' % get_metavar(1)
                elif metavar_len > 1:
                    f_string = ' [%s]' * (metavar_len - 1)
                    f_string = '[%s{}]'.format(f_string)
                    result = f_string % get_metavar(metavar_len)
                else:
                    raise ValueError('The "metavar" attribute cannot provide an empty tuple.')
        elif action.nargs == argparse.ONE_OR_MORE:
            if action.metavar is None:
                result = '[%s [%s ...]]' % get_metavar(2)
            else:
                if isinstance(action.metavar, str):
                    metavar_len = 1
                else:
                    metavar_len = len(action.metavar)
                if metavar_len == 1:
                    result = '[%s]' % get_metavar(1)
                elif metavar_len > 1:
                    f_string = ' [%s]' * (metavar_len - 1)
                    f_string = '[%s{}]'.format(f_string)
                    result = f_string % get_metavar(metavar_len)
                else:
                    raise ValueError('The "metavar" attribute cannot provide an empty tuple.')
        elif action.nargs == argparse.REMAINDER:
            result = '...'
        elif action.nargs == argparse.PARSER:
            result = '%s ...' % get_metavar(1)
        else:
            formats = ['%s' for _ in range(action.nargs)]
            result = ' '.join(formats) % get_metavar(action.nargs)
        return result

    # Abbreviate shorthand help
    def _format_action_invocation(self, action):
        if not action.option_strings:
            default = self._get_default_metavar_for_positional(action)
            metavar, = self._metavar_formatter(action, default)(1)
            return metavar

        else:
            parts = []

            # if the Optional doesn't take a value, format is:
            #    -s, --long
            if action.nargs == 0:
                parts.extend(action.option_strings)

            # if the Optional takes a value, format is:
            #    -s ARGS, --long ARGS
            else:
                default = self._get_default_metavar_for_optional(action)
                args_string = self._format_args(action, default)
                parts.extend(action.option_strings[:-1])
                parts.append('%s %s' % (action.option_strings[-1], args_string))
                # for option_string in action.option_strings:
                #     parts.append('%s %s' % (option_string, args_string))

            return ', '.join(parts)



class FixArgValue(argparse.Action):
    """Fix incorrect allocation of values ​​due to resolution reasons
    :param check_arg: The name of the arg. to be checked, its type must be different from the current arg.
    """
    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None,
                 check_arg=None):   # Add 'check_arg' arg
        argparse.Action.__init__(self,
                                 option_strings=option_strings,
                                 dest=dest,
                                 nargs=nargs,
                                 const=const,
                                 default=default,
                                 type=type,
                                 choices=choices,
                                 required=required,
                                 help=help,
                                 metavar=metavar)
        self.check_arg = check_arg
        # print('Initializing CustomAction')
        # for name, value in sorted(locals().items()):
        #     if name == 'self' or value is None:
        #         continue
        #     print('init value: {} = {!r}'.format(name, value))
        # return
    def __call__(self, parser, namespace, values, option_string=None):
        # print('- dest = {}'.format(self.dest))
        # print('- values = {!r}'.format(values))
        # print('- namespace = {}'.format(namespace))
        # print('- parser = {}'.format(parser))
        # print('- option_string = {!r}'.format(option_string))
        # import pprint
        # pprint.pprint('{}'.format(parser.__dict__['_registries']))
        # for item in parser.__dict__['_optionals']:
        #     pprint.pprint(item)

        #parser.__dict__._StoreAction.dest
        if values:
            '''Normal assignment if the current value exists
            Type conversion will be performed before accon, 
            so there is no need to perform type conversion again.'''
            setattr(namespace, self.dest, values)
        else:
            # Get the value of the parameter to check
            check_arg_value = getattr(namespace, self.check_arg, None)

            if self.type is None:
                self.type = str
            try:
                # Use the type checker of this parameter to check the value of `check_arg`.
                if isinstance(check_arg_value, (list, tuple)):
                    [self.type(value) for value in check_arg_value]
                    value = check_arg_value
                else:
                    value = self.type(check_arg_value)
            except Exception:
                # Error, give up fix, use default value
                setattr(namespace, self.dest, self.default)
            else:
                # Deprive the value from checked parameters
                setattr(namespace, self.dest, value)
                # Reassign the checked parameter with its default value
                for item in parser.__dict__['_actions']:
                    if item.dest == self.check_arg:
                        setattr(namespace, self.check_arg, item.default)
                        break

@mboot.global_error_handler
def main():
    parser = argparse.ArgumentParser(prog='mboot', description='A python mboot with user interface.', 
        formatter_class=MBootHelpFormatter, add_help=False)#, usage='%(prog)s [peripheral option] [other options] []')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-u', '--usb', nargs='?', const=[], default=None, 
        help='Use usb peripheral, such as "-u VIDPID", "-u"', metavar='vid,pid')
    group.add_argument('-p', '--uart', nargs='*', help='Use uart peripheral', metavar=('port', 'speed'))
    group.add_argument('-s', '--spi', nargs='*', help='Use spi peripheral, '
        'such as "-s VIDPID SPEED", "-s VIDPID", "-s SPEED", "-s"', metavar=('vid,pid', 'speed'))
    group.add_argument('-i', '--i2c', nargs='*', help='Use i2c peripheral', metavar=('vid,pid', 'speed'))

    parser.add_argument('-t', '--timeout', type=int, help='Maximum wait time for the change of the transceiver status in a single atomic operation, '
        'it is only valid for the "flash-erase-*" command and only changes the timeout of the ack after sending the packet, '
        'which is invalid for the timeout in read phase.')
    # parser.add_argument('-d', '--debug', action='store_true', help='Debug level: 0-off, 1-info, 2-debug')
    parser.add_argument('-d', '--debug', nargs='?', type=int, choices=range(0, 3), const=1, default=0, help='Debug level: 0-off, 1-info, 2-debug')
    parser.add_argument('-o', '--origin', nargs=argparse.REMAINDER, help='MCU Boot Original Interface')
    parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Show this help message and exit.')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 1.0', help="Show program's version number and exit.")
    # requiredNamed = parser.add_argument_group('required named arguments')
    # requiredNamed.add_argument('-info', action='store_true', help='Get MCU info (mboot properties)')

    subparsers = parser.add_subparsers(title='MCU Boot User Interface', prog='mboot [options]')
    
    parser_info = subparsers.add_parser('info', help='Get MCU info (mboot properties)', add_help=False)
    parser_info.add_argument('memory_id', nargs='?', type=check_int, default=0, 
        help='External memory id, Display external memory information if it is already executed configure-memory')
    parser_info.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Show this help message and exit.')

    parser_write = subparsers.add_parser('write', help='Write data into MCU memory', add_help=False)
    parser_write.add_argument('address', type=check_int, nargs='?', help='Start address, '
        'the arg can be omitted if file end with ".srec", ".s19", ".hex", ".ihex" that contains the address')
    parser_write.add_argument('filename', help='File to be written')
    parser_write.add_argument('memory_id', nargs='?', type=check_int, default=0, help='External memory id')
    parser_write.add_argument('-o', '--offset', type=check_int, default=0, help='Offset address')
    parser_write.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Show this help message and exit.')

    parser_read = subparsers.add_parser('read', help='Read data from MCU memory', add_help=False)
    parser_read.add_argument('address', type=check_int, help='Start address')
    parser_read.add_argument('length', type=check_int, default=0x100, help='Read data length')
    parser_read.add_argument('filename', nargs='?', help='File to be written')
    parser_read.add_argument('memory_id', nargs='?', type=check_int, action=FixArgValue, check_arg='filename', default=0, help='External memory id')
    parser_read.add_argument('-c', '--compress', action='store_true', help='Compress dump output.')
    parser_read.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Show this help message and exit.')

    parser_fill = subparsers.add_parser('fill', help='Fill MCU memory with specified pattern', add_help=False)
    parser_fill.add_argument('address', type=check_int, help='Start address')
    parser_fill.add_argument('byte_count', type=check_int, help='Total length of padding, count of bytes')
    parser_fill.add_argument('pattern', type=check_int, help='The pattern used for padding, (default: 0xFFFFFFFF)')
    parser_fill.add_argument('unit', nargs='?', choices=['word', 'short', 'byte'], default='word', 
        help='Process pattern according to word, short(half-word), byte')
    parser_fill.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Show this help message and exit.')

    parser_erase = subparsers.add_parser('erase', help='Erase MCU memory', add_help=False)
    parser_erase.add_argument('address', type=check_int, help='Start address')
    parser_erase.add_argument('length', type=check_int, default=0x100, help='Erase data length')
    parser_erase.add_argument('memory_id', nargs='?', type=check_int, default=0, help='External memory id')
    parser_erase.add_argument('-a', '--all', action='store_true', help='Erase complete MCU memory')
    parser_erase.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Show this help message and exit.')

    parser_unlock = subparsers.add_parser('unlock', help='Unlock MCU', add_help=False)
    parser_unlock.add_argument('-k', '--key', type=check_key, help='Use backdoor key as ASCI = S:123...8 or HEX = X:010203...08')
    parser_unlock.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Show this help message and exit.')

    parser_reset = subparsers.add_parser('reset', help='Reset MCU', add_help=False)
    parser_reset.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Show this help message and exit.')

    cmd = parse_args(parser, subparsers)
    log_level = [logging.WARNING, logging.INFO, logging.DEBUG]
    if cmd.origin and cmd.debug < 2:
        cmd.debug += 1
    logging.basicConfig(level=log_level[cmd.debug])

    # print(cmd)

    mb = mboot.McuBoot()
    mb.cli_mode = True  # this is cli mode

    # Added the feature to display the original interface help
    if cmd.origin and ('-h' in cmd.origin or '--help' in cmd.origin):
        attr = cmd.origin[0].replace('-', '_')
        func = getattr(mb, attr, None)
        if func:
            print('\n  '.join(line.strip() for line in func.__doc__.split('\n ')))
            sys.exit(0) # Normal exit
        else:
            raise McuBootGenericError('invalid command:{}'.format(cmd.origin[0]))

    if cmd.usb is not None:
        vid_pid = parse_peripheral(Interface.USB.name, cmd.usb)[0]
        mb.open_usb(vid_pid)
        # device = RawHID.enumerate(*vid_pid)[0]
        # mb.open_usb(device)
    elif cmd.uart is not None:
        port, baudrate = parse_peripheral(Interface.UART.name, cmd.uart)
        mb.open_uart(port, baudrate)
    elif cmd.spi is not None:
        vid_pid, speed = parse_peripheral(Interface.SPI.name, cmd.spi)
        mb.open_spi(vid_pid, speed, 0)
    elif cmd.i2c is not None:
        vid_pid, speed = parse_peripheral(Interface.I2C.name, cmd.i2c)
        mb.open_i2c(vid_pid, speed)
    else:
        raise McuBootGenericError('You need to choose a peripheral for communication.')

    # mb.get_memory_range()

    if cmd.info:
        info(mb, cmd.info.memory_id)

    if cmd.write:
        args = cmd.write
        write(mb, args.address, args.filename, args.memory_id, args.offset)
        print(" Wrote Successfully.")
        # if check_method_arg_number(write, len(cmd.write)+1):
        #     args = convert_arg_to_int(cmd.write)
        #     write(mb, *args)

    if cmd.read:
        args = cmd.read
        read(mb, args.address, args.length, args.filename, args.memory_id, args.compress)

    if cmd.fill:
        args = cmd.fill
        fill(mb, args.address, args.byte_count, args.pattern, args.unit)
        print(" Filled Successfully.")

    if cmd.erase:
        args = cmd.erase
        erase(mb, args.address, args.length, args.memory_id, args.all)
        print(" Erased Successfully.")

    if cmd.unlock:
        args = cmd.unlock
        unlock(mb, args.key)
        print(" Unlocked Successfully.")

    if cmd.reset:
        mb.reset()
        print(' Reset OK')

    if cmd.origin:
        mb.timeout = cmd.timeout or mb.timeout
        attr = cmd.origin[0].replace('-', '_')
        func = getattr(mb, attr, None)

        if func:
            cmd_args = cmd.origin[1:]
            # if cmd_args[0].lower().startswith('-h'):    # cmd_args[0].lower() == '-h' or cmd_args[0].lower() == '--help':
            #     print('\n  '.join(line.strip() for line in func.__doc__.split('\n ')))
            if check_method_arg_number(func, len(cmd_args)):
                if attr == 'flash_security_disable':
                    args = cmd_args
                else:
                    args = convert_arg_to_int(cmd_args)
                data = func(*args)
                if attr == 'read_memory':
                    print('\n', hexdump(data, args[0], False))
            else:
                raise McuBootGenericError('invalid arguments:{}'.format(cmd_args))
        else:
            raise McuBootGenericError('invalid command:{}'.format(cmd.origin[0]))

    mb.close()

if __name__ == "__main__":
    main()