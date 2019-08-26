[English](how_to_install_libusb.md) | 简体中文

### Overviews

`libusb`是一个C语言库，提供对USB设备的通用访问。它旨在供开发人员使用，以便于生成与USB硬件通信的应用程序。

### Installation

因为`pyFtdi`依赖于`PyUSB`，后者本身依赖于`libusb`，并且它不会自动安装，所以我们需要手动安装它，你可以先尝试`mboot`能否正常使用，然后决定是否安装它。

#### For Linux

如果您使用的是Linux，那么您的发行版可能已包含libusb，因此您可能只需要在源代码中引用libusb标头。

对于Debian / Ubuntu：

你应该首先安装`libusb`：

```sh
$ apt-get install libusb-1.0
```

然后，您需要创建一个udev配置文件，以允许用户空间进程访问FTDI设备。有很多方法可以配置udev，这是一个典型的设置：

```
# /etc/udev/rules.d/11-ftdi.rules
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6001", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6011", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6010", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6014", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6015", GROUP="plugdev", MODE="0666"
```

创建此文件后，您需要拔出/插回FTDI设备，以便udev加载匹配设备的规则。

使用此设置，请务必将想要运行PyFtdi的用户添加到plugdev组，例如：

```sh
$ sudo adduser $USER plugdev
```

请记住，您需要注销/登录才能使上述命令生效。

#### For windows

请记住，如果您的目标设备不是HID，则必须先安装驱动程序，然后才能使用`libusb`与其进行通信。目前，这意味着安装一个Microsoft的`WinUSB`，`libusb-win32`或`libusbK`驱动程序。

您可以使用[Zadig][1]来安装它，**Zadig**是一个安装通用USB驱动程序的Windows应用程序，例如[WinUSB][3]，[libusb-win32 / libusb0.sys][4]或[libusbK][5]，帮助您访问USB设备。你可以找到帮助[这里][2]。

请注意，如果您看不到列出的设备，则可能意味着它已经安装了驱动程序，因为Windows可能会自动安装驱动程序。为了显示具有已安装驱动程序的设备，您可以转到`Options`菜单并选择`List All Devices`。

![Zadig](.\image\Zadig.jpg)

或者您可以手动安装上述任何驱动程序，成功安装`libusb-win32`的过程如下：

1. 从[Libusb win32][6]下载`Libusb-win32-devel-filter`
2. 拔出不必要的USB设备
3. 运行并选择你需要安装驱动程序的设备
4. 进入`Libusb-Win32`开始菜单并运行`install all class filters.exe`

### Some references

* [libusb/libusb Wiki](https://github.com/libusb/libusb/wiki)
* [Installation — PyFtdi documentation](https://eblot.github.io/pyftdi/installation.html)

[1]:https://zadig.akeo.ie/
[2]:https://github.com/pbatard/libwdi/wiki/Zadig
[3]:https://docs.microsoft.com/en-us/windows-hardware/drivers/usbcon/winusbs
[4]:https://sourceforge.net/p/libusb-win32/wiki/Home/
[5]:http://libusbk.sourceforge.net/UsbK3/
[6]:https://sourceforge.net/projects/libusb-win32/files/libusb-win32-releases/
