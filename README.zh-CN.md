[English](README.md) | 简体中文

## pyMBoot

[![Build Status](https://travis-ci.org/nxdhf/pyMBoot.svg?branch=master)](https://travis-ci.org/nxdhf/pyMBoot) [![Python Version](https://img.shields.io/badge/python-3-blue)](https://www.python.org) [![License](https://img.shields.io/github/license/nxdhf/pyMBoot)](https://github.com/nxdhf/pyMBoot/blob/master/LICENSE)

`pyMBoot`是一个基于python的开源库，用于通过嵌入式MCUBOOT(MCU Bootloader)查看，配置恩智浦微控制器和其中的固件。它致力于提供一个人性化的界面，使操作更容易。

这个项目是[pyMBoot][1]的`fork`，并加入对`uart`，`spi`，`i2c`外围设备的支持。除此之外，我使用`argprase`而不是`click`来重写CLI部分，这提供了一个更加用户友好的界面，更加一致的接口，你可以省略一些固定的参数。与原始项目相比，CLI中添加了对`MCU Boot Original Interface`的直接调用。并且添加错误捕获和工具，现在可以直接调用函数，而无需用户捕获异常。

> 该项目仍处于发展阶段。请测试并报告已成立的问题。

### Dependencies

- [Python 3.x](https://www.python.org) - The interpreter
- [bincopy](https://github.com/eerimoq/bincopy) - Python package for parsing S-Record, Intel HEX and TI-TXT files.
- [easy_enum](https://github.com/molejar/pyEnum) - User friendly implementation of documented Enum type for Python language.
- [PyUSB](https://github.com/pyusb/pyusb) - Python package to access USB devices in Linux OS.
- [PyWinUSB](https://github.com/rene-aguirre/pywinusb) - Python package that simplifies USB-HID communications on Windows OS.
- [pyserial](https://github.com/pyserial/pyserial) - Python package for communication over Serial port in Linux and Windows OS.
- [pyftdi](https://github.com/eblot/pyftdi): FTDI device driver written in pure Python

### Installation

对于一般用户，可以从`.whl`分发包安装它，你可以在项目的发布(Release)中找到它并下载它，运行以下命令来安装它：

```sh
pip install mboot-*.whl
```

你也可以通过克隆手动安装它的最新版本：

```sh
pip install -U https://github.com/nxdhf/pyMBoot/archive/master.zip
```

在开发的情况下，建议使用虚拟环境，通过克隆github源来安装它：

```sh
$ git clone https://github.com/nxdhf/pyMBoot
$ cd pyMBoot
$ pipenv install            # pipenv will automatically install dependencies by requirements.txt
$ pipenv shell
$ pip install -e .
```

为了通过`spi`，`i2c`协议与设备通信，你需要一个FTDI设备作为桥接器。有关详细信息，请参阅[How to install libusb](doc/how_to_install_libusb.zh-CN.md)

### mboot core

以下示例显示如何在代码中使用`mboot`模块。

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

通过`uart`, `spi`, `i2c`进行交互与上面类似。

### mboot CLI

`pyMBoot`与命令行实用程序`mboot`一起分发，它提供了该库的完整功能。如果你在shell中输入`mboot`并敲击enter，那么你会得到它的用法描述。要获得单个命令的帮助，只需使用`mboot subcommand -h/--help`。

mboot的所有可用命令如下：

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

要使用`mboot`，你需要选择连接的外围设备的方式，例如`--usb`，`--uart`，`--spi`，`--i2c`选项。当然，你只能选择其中一个并输入相应的值，`VIDPID`可以用`:`或`,`来分割。有关具体用法，请参阅上面的帮助。如果选项后没有添加任何值，`mboot`将尝试自动搜索设备。

超时(timeout)指在单个原子操作中更改收发器状态的最长等待时间。`-t` /`--timeout`选项仅对`flash-erase-region`，`flash-erase-all`，`flash_erase-all-unsecure`命令有效，并且仅在发送数据包后改变ack的超时时间，这对于读取阶段的超时是无效的。

你可以使用`-d` /`--debug`选项打开日志输出。 `-d`用于输出信息(info)，`-d 2`用于输出调试(debugs)，它将打印发送和接收的详细信息，并在发生错误时输出回调，通常只有在你开发框架时使用。请注意，`MCU Boot Original Interface`默认级别比`MCU Boot User Interface`高一级，除非它已经是可以设置的最高级别。

`mboot`提供了两种接口`MCU Boot User Interface`和`MCU Boot Original Interface`

#### MCU Boot User Interface

`MCU Boot User Interface`是一个增强的`MCU Boot Original Interface`。它执行一些额外的操作来简化你的输入。例如，当你使用`write`命令时，如果写入对象是闪存，则它将首先被擦除。此外，它还包含范围检查等。

你可以使用命令`mboot <user interface command name> -h`来查看关于`User Interface`子命令的帮助。

##### info

你可以通过输入子命令`info`来查看当前设备信息。如果输入`memory_id`选项，它将显示有关外部存储器的其他信息（如果已设置外部存储器）。使用时不要忘记使用`-u`，`-p`，`-s`，`-i`选项来选择连接的方式。

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

子命令`read`可以读取RAM和闪存数据。对于外部存储器，你需要指定`memory_id`，并且需要确保已设置外部存储器，你可以使用`--exconf`选项快速设置它。设置`--compress`选项后，`*`将用于填充重复的行。其余的参数与`MCU Original Interface`的`read-memory`命令相同。

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

子命令`write`可以写入RAM和闪存数据。对于外部存储器，你需要指定`memory_id`，并且需要确保已设置外部存储器，你可以使用`--exconf`选项快速设置它。该子命令将在写入闪存之前自动执行擦除命令，你可以使用`--no_erase`标志禁用自动擦除。其余的参数与`MCU Original Interface`的`write-memory`命令相同。值得注意的是，该命令支持读取不同类型的文件，而有些文件具有`address`参数，因此命令中的位置参数`address`可以省略。

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

子命令`fill`可以将`pattern`填充到RAM和flash中，该子命令不支持外部存储器。它会在写入闪存之前自动执行擦除命令，你可以使用`--no_erase`标志禁用自动擦除。其余的参数与`MCU Original Interface`的`fill-memory`命令相同。

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

子命令`erase`可以擦除闪存中的数据，对于外部存储器，需要指定`memory_id`，并且需要确保已设置外部存储器，可以使用`--exconf`选项快速设置它。注意，当选项`--all`打开时，进入全芯片擦除模式。此时，可以省略擦除`address`。否则，不应该省略。 `length`的默认值是0x100，但实际擦除时因为块的大小不同可能会超过此值。

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

子命令`unlock`用于解锁MCU内存。我将来可能会支持jlink的`unlock`命令。

```sh
$ mboot unlock -h
Usage: mboot [options] unlock [-k KEY] [-h]

optional arguments:
  -k, --key KEY  Use backdoor key as ASCI = S:123...8 or HEX = X:010203...08
                 (default: None)
  -h, --help     Show this help message and exit.
```

#### reset

目前它与`MCU original Interface`的`reset`命令没有什么不同。

```sh
$ mboot reset -h
Usage: mboot [options] reset [-h]

optional arguments:
  -h, --help  Show this help message and exit.
```

[这里](doc/usage_example.md#MCU%20Boot%20User%20Interface)有一些具体实例。

#### MCU Boot Original Interface

有关`MCU Boot Original Interface`的使用，请参阅[MCU Bootloader参考手册](https://www.nxp.com/docs/en/reference-manual/MCUBOOTRM.pdf）。区别在于`blhost`使用`--`作为分隔符，而`mboot`使用`-o`。当然，指定当前外围设备的类型不同，`mboot`使用`-s`，`-i`来表达`spi`和`i2c`。你也可以使用`-h`来查看帮助，它会直接打印`docstring`。

[这里](doc/usage_example.md#MCU%20Boot%20User%20Interface)有一些具体实例。



[1]:https://github.com/molejar/pyMBoot
