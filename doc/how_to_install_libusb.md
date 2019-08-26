English | [简体中文](how_to_install_libusb.zh-CN.md)

### Overviews

`libusb` is a C library that provides generic access to USB devices. It is intended to be used by developers to facilitate the production of applications that communicate with USB hardware.

### Installation

Because `pyFtdi` relies on `PyUSB`, which itself depends on `libusb`, and it won't be installed automatically, so we need to install it manually, You can try `mboot` first, then decide whether to install it.

#### For Linux

If you are using Linux, chances are your distribution already includes libusb, so you probably just need to reference the libusb header in your source.

For Debian/Ubuntu:

You should install `libusb` first:

```sh
$ sudo apt install libusb-1.0
```

then you need to create a udev configuration file to allow user-space processes to access to the FTDI devices. There are many ways to configure udev, here is a typical setup:

```
# /etc/udev/rules.d/11-ftdi.rules
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6001", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6011", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6010", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6014", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6015", GROUP="plugdev", MODE="0666"
```

You need to unplug / plug back the FTDI device once this file has been created so that udev loads the rules for the matching device.

With this setup, be sure to add users that want to run PyFtdi to the plugdev group, e.g.

```sh
$ sudo adduser $USER plugdev
```

Remember that you need to log out / log in to get the above command effective.

#### For windows

If your target device is not HID, you must install a driver before you can communicate with it using `libusb`. Currently, this means installing one of Microsoft's `WinUSB`, `libusb-win32` or `libusbK` drivers.

You can use [Zadig][1] to install this, **Zadig** is a Windows application that installs generic USB drivers, such as [WinUSB][3], [libusb-win32/libusb0.sys][4] or [libusbK][5], to help you access USB devices. you can find help [here][2].

Note if you cannot see your device listed, then it probably means that it already has a driver installed, because windows may automatically install the driver. In order to display the device with the installed driver, you can go to the `Options` menu and select `List All Devices`.

![Zadig](.\image\Zadig.jpg)

Or you can manually install any of the above drivers, a process of successfully installing `libusb-win32` as follows:

1. download `Libusb-win32-devel-filter` from [Libusb win32][6]
2. Remove unnecessary usb devices
3. run and select the device you need to install the driver
4. go into the `Libusb-Win32` start menu and run `install all class filters.exe`

### Some references

* [libusb/libusb Wiki](https://github.com/libusb/libusb/wiki)
* [Installation — PyFtdi documentation](https://eblot.github.io/pyftdi/installation.html)

[1]:https://zadig.akeo.ie/
[2]:https://github.com/pbatard/libwdi/wiki/Zadig
[3]:https://docs.microsoft.com/en-us/windows-hardware/drivers/usbcon/winusbs
[4]:https://sourceforge.net/p/libusb-win32/wiki/Home/
[5]:http://libusbk.sourceforge.net/UsbK3/
[6]:https://sourceforge.net/projects/libusb-win32/files/libusb-win32-releases/
