English | [简体中文](README.zh-CN.md)

## pyMBoot

[![Build Status](https://travis-ci.org/nxdhf/pyMBoot.svg?branch=master)](https://travis-ci.org/nxdhf/pyMBoot) [![Python Version](https://img.shields.io/badge/python-3-blue)](https://www.python.org) [![License](https://img.shields.io/github/license/nxdhf/pyMBoot)](https://github.com/nxdhf/pyMBoot/blob/master/LICENSE)

`pyMBoot` is an Open Source python based library for viewing, configuring NXP Microcontrolers and upgrading the firmware in it via embedded MCUBOOT (MCU Bootloader). It is committed to providing a human interface that makes operation easier.

This project come from the fork of [pyMBoot][1], and join the support for `uart`, `spi`, `i2c` peripherals. In addition to this, I uses `argprase` instead of `click` to rewrite the CLI part, this provides a more user-friendly interface, more consistent and you can omit some fixed parameters. Compared with the original project, a new direct call to the `MCU Boot Original Interface` is added in CLI. With the addition of error capture and tools, it is now possible to call functions directly without the need for users to catch exceptions.

> This project is still in developing phase. Please, test it and report founded issues.

### Dependencies

- [Python 3.x](https://www.python.org) - The interpreter
- [bincopy](https://github.com/eerimoq/bincopy) - Python package for parsing S-Record, Intel HEX and TI-TXT files.
- [easy_enum](https://github.com/molejar/pyEnum) - User friendly implementation of documented Enum type for Python language.
- [PyUSB](https://github.com/pyusb/pyusb) - Python package to access USB devices in Linux OS.
- [PyWinUSB](https://github.com/rene-aguirre/pywinusb) - Python package that simplifies USB-HID communications on Windows OS.
- [pyserial](https://github.com/pyserial/pyserial) - Python package for communication over Serial port in Linux and Windows OS.
- [pyftdi](https://github.com/eblot/pyftdi): FTDI device driver written in pure Python

### Installation

For general users, install it from the .whl distribution package, you can find it in the project release and download it, run the following command to install it:

```sh
pip3 install mboot-*.whl
```

you can also install the latest version of it manually by cloning:

```sh
pip3 install -U https://github.com/nxdhf/pyMBoot/archive/master.zip
```

In case of development, It is recommended to use a virtual environment(Because the package installed with '-e' has problems on unbuntu that cannot be uninstalled), install it from cloned github sources:

```sh
$ git clone https://github.com/nxdhf/pyMBoot
$ cd pyMBoot
$ pipenv install            # pipenv will automatically install dependencies by requirements.txt
$ pipenv shell
$ pip3 install -e .
```

Note that it is recommended to install with root privileges on Linux, so that it will be installed in the global directory instead of the user directory. If you do not install it with root privileges, you may need to manually add the user directory to the `$PATH`, otherwise you will get an error when using the command line. In order to solve this problem, please refer to
[usage problem](doc/usage_problem.md#Installation%20was%20successful%20but%20the%20CLI%20prompt%20mboot%20command%20was%20not%20found?)

In order to communicate with the device via `spi`, `i2c` protocol, you need a FTDI device as a bridge, For details, see [How to install libusb](doc/how_to_install_libusb.md)

### mboot core

The following example is showing how to use `mboot` module in your code.

``` python
import mboot
import logging

# Scan for connected MCU's
product_name, vid_pid = mboot.scan_usb()
# Create mboot instance
mb = mboot.McuBoot(level=logging.INFO)  # output log
# Still just an "empty" object
if not mb:
  print("Not open the device yet.")
# Connect to first USB device from all founded
if mb.open_usb(vid_pid):  # mb.open_uart(port, baudrate), mb.open_spi(vid_pid, freq, mode), mb.open_i2c(vid_pid, freq),
    # Read MCU memory: 100 bytes from address 0
    data = mb.read_memory(start_address=0, length=100)

    # Other commands
    # ...

    # Close USB port if finish
    mb.close()
else:
    print('open usb failed.')

    # Open usb failed operation
    # ...
```

communicate through `uart`, `spi`, `i2c` is similar to the above.

### mboot CLI

`pyMBoot` is distributed with command-line utility `mboot`, which presents the complete functionality of this library.
If you write `mboot` into shell and click enter, then you get the description of its usage. For getting the help of individual commands just use `mboot subcommand -h/--help`.

All available commands for mboot are as follows:

```sh
$ mboot -h
Usage: mboot [-u [vid,pid] | -p [port [speed]] | -s [vid,pid [speed]] | -i
             [vid,pid [speed]]] [-t TIMEOUT] [-d [{0,1,2}]] [-o ...] [-h] [-v]
             {info,write,read,fill,erase,unlock,reset} ...

A python mboot with user interface.

optional arguments:
  -u, --usb [vid,pid]              Use usb peripheral, such as "-u VIDPID", "-u"
                                   (default: None)
  -p, --uart [port [speed]]        Use uart peripheral, such as "-p PORT SPEED", "-p
                                   PORT", "-p SPEED", "-p" (default: None)
  -s, --spi [vid,pid [speed]]      Use spi peripheral, such as "-s VIDPID SPEED", "-s
                                   VIDPID", "-s SPEED", "-s" (default: None)
  -i, --i2c [vid,pid [speed]]      Use i2c peripheral, such as "-i VIDPID SPEED", "-i
                                   VIDPID", "-i SPEED", "-i" (default: None)
  -t, --timeout TIMEOUT            Maximum wait time(Unit: s) for the change of the
                                   transceiver status in a single atomic operation,
                                   it is only valid for the "flash-erase-*" command
                                   and only changes the timeout of the ack after
                                   sending the packet, which is invalid for the
                                   timeout in read phase. (default: None)
  -d, --debug [{0,1,2}]            Debug level: 0-off, 1-info, 2-debug (default: 0)
  -o, --origin ...                 MCU Boot Original Interface (default: None)
  -h, --help                       Show this help message and exit.
  -v, --version                    Show program's version number and exit.

MCU Boot User Interface:
  {info,write,read,fill,erase,unlock,reset}
    info                           Get MCU info (mboot properties)
    write                          Write data into MCU memory
    read                           Read data from MCU memory
    fill                           Fill MCU memory with specified pattern
    erase                          Erase MCU memory
    unlock                         Unlock MCU
    reset                          Reset MCU
```

To use `mboot` you need to choose the connected peripherals, such as `--usb`, `--uart`, `--spi`, `--i2c` option. Of course, you can only choose one of them and enter the corresponding value, `VIDPID` can be split using `:` or `,`. For specific usage, see the help above. If no value is added after the option, `mboot` will try to search for the device automatically.

Timeout means the maximum wait time for the change of the transceiver status in a single atomic operation. The `-t`/`--timeout` option is only valid for the `flash-erase-region`, `flash-erase-all`, `flash_erase-all-unsecure` command and only changes the timeout of the ack after sending the packet, which is invalid for the timeout in read phase.

You can use the `-d`/`--debug` option to turn on log output. `-d` for output info, `-d 2` for output debug, which will print the details of the send and receive and output a callback when an error occurs, usually only if you develop the framework. Note that `MCU Boot Original Interface` default level is one level higher than `MCU Boot User Interface`, unless it is already the highest level that can be set.

`mboot` provides two interfaces: `MCU Boot User Interface` and `MCU Boot Original Interface`

#### MCU Boot User Interface

`MCU Boot User Interface` is an enhanced `MCU Boot Original Interface`. It performs some extra operations to simplify your input. For example, when you use the `write` command, if the write object is flash, it will be erased first. In addition, it also contains the range inspection, etc.

You can use the command `mboot <user interface command name> -h` to see the help of User Interface subcommand.

##### info

You can view the current device information by entering the subcommand `info`, If you enter the `memory_id`, it will display additional information about the external memory(if external memory has been set). Don't forget to use `-u`, `-p`, `-s`, `-i` option to select the peripherals.

```sh
$ mboot info -h
Usage: mboot [options] info [memory_id] [-e ...] [-h]

positional arguments:
  memory_id           External memory id, Display external memory information if it
                      is already executed configure-memory (default: 0)

optional arguments:
  -e, --exconf ...  Set external memory address and settings, such as
                      "fill_config_address config_word1 [config_word2 [...]]", only
                      the first time you need to set (default: None)
  -h, --help          Show this help message and exit.
```

#### read

Subcommand `read` can read RAM and flash data. For external memory, you need to specify the `memory_id`, and you need to make sure the external memory has been set, you can quickly set it with the `--exconf` option. After `--compress` option is set, the `*` will be used to fill the duplicate rows. The rest of the args are the same as the `read-memory` command of the `MCU Original Interface`.

```sh
$ mboot read -h
Usage: mboot [options] read address length [filename] [memory_id] [-c] [-e ...] [-h]

positional arguments:
  address             Start address
  length              Read data length
  filename            File to be written (default: None)
  memory_id           External memory id (default: 0)

optional arguments:
  -c, --compress      Compress dump output. (default: False)
  -e, --exconf ...  Set external memory address and settings, such as
                      "fill_config_address config_word1 [config_word2 [...]]", only
                      the first time you need to set (default: None)
  -h, --help          Show this help message and exit.
```

#### write

Subcommand `write` can write RAM and flash data. For external memory, you need to specify the `memory_id`, and you need to make sure the external memory has been set, you can quickly set it with the `--exconf` option. This subcommand will automatically execute the erase command before writing to flash, you can disable auto-erase by using `--no_erase` flag. The rest of the args are the same as the `write-memory` command of the `MCU Original Interface`. It is noteworthy that this command supports reading different types of files, some files have `address` parameters, so the position parameter `address` in the command can be omitted.

```sh
$ mboot write -h
Usage: mboot [options] write [address] filename [memory_id]
                             [-o OFFSET] [--no_erase] [-e ...] [-h]

positional arguments:
  address              Start address, the arg can be omitted if file end with
                       ".srec", ".s19", ".hex", ".ihex" that contains the address
                       (default: None)
  filename             File to be written
  memory_id            External memory id (default: 0)

optional arguments:
  -o, --offset OFFSET  File offset address (default: 0)
  --no_erase           Do not automatically erase before writing. (default: False)
  -e, --exconf ...   Set external memory address and settings, such as
                       "fill_config_address config_word1 [config_word2 [...]]", only
                       the first time you need to set (default: None)
  -h, --help           Show this help message and exit.
```

#### fill

Subcommand `fill` can fill `pattern` to RAM and flash, This subcommand do not support external memory. It will automatically execute the erase command before writing to flash, you can disable auto-erase by using `--no_erase` flag. The rest of the args are the same as the `fill-memory` command of the `MCU Original Interface`.

```sh
$ mboot fill -h
Usage: mboot [options] fill address byte_count pattern [{word,short,byte}]
                            [--no_erase] [-h]

positional arguments:
  address            Start address
  byte_count         Total length of padding, count of bytes
  pattern            The pattern used for padding, (default: 0xFFFFFFFF)
  {word,short,byte}  Process pattern according to word, short(half-word), byte
                     (default: word)

optional arguments:
  --no_erase         Do not automatically erase before writing. (default: False)
  -h, --help         Show this help message and exit.
```

#### erase

Subcommand `erase` can erase data in the flash, For external memory, you need to specify the `memory_id`, and you need to make sure the external memory has been set, you can quickly set it with the `--exconf` option. Note that when the option `--all` is turned on, the full-chip erase mode is entered. At this time, the erase `address` can be omitted. Otherwise, it should not be omitted. The default value of `length` is 0x100, but the actual erase may exceed this value because of the size of the block.

```sh
$ mboot erase -h
Usage: mboot [options] erase [address] [length] [memory_id] [-a] [-e ...] [-h]

positional arguments:
  address             Start address (default: None)
  length              Erase data length (default: 256)
  memory_id           External memory id (default: 0)

optional arguments:
  -a, --all           Erase complete MCU memory (default: False)
  -e, --exconf ...  Set external memory address and settings, such as
                      "fill_config_address config_word1 [config_word2 [...]]", only
                      the first time you need to set (default: None)
  -h, --help          Show this help message and exit.
```

#### unlock

Subcommand `unlock` is used to unlock MCU memory. I may support the jlink `unlock` command in the future.

```sh
$ mboot unlock -h
Usage: mboot [options] unlock [-k KEY] [-h]

optional arguments:
  -k, --key KEY  Use backdoor key as ASCI = S:123...8 or HEX = X:010203...08
                 (default: None)
  -h, --help     Show this help message and exit.
```

#### reset

Currently it is no different from the `reset` command of `MCU original Interface`.

```sh
$ mboot reset -h
Usage: mboot [options] reset [-h]

optional arguments:
  -h, --help  Show this help message and exit.
```

[Here](doc/usage_example.md#MCU%20Boot%20User%20Interface) are some examples.

#### MCU Boot Original Interface

For the use of `MCU Boot Original Interface`, please refer to [MCU Bootloader Reference Manual](https://www.nxp.com/docs/en/reference-manual/MCUBOOTRM.pdf). The difference is that `blhost` uses `--` as a separator and `mboot` uses `-o`. Of course, the type of the current peripheral is specified differently, `mboot` use `-s`, `-i` to express `spi` and `i2c`. You can also use `-h` to view help, it will print `docstring` directly.

[Here](doc/usage_example.md#MCU%20Boot%20Original%20Interface) are some examples.



[1]:https://github.com/molejar/pyMBoot
