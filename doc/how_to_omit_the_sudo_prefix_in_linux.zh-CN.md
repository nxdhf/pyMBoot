[English](how_to_omit_the_sudo_prefix_in_linux.md) | 简体中文

### Overview

因为`mboot`涉及到了与底层设备的交互，所以在`linux`中我们需要在命令的前面加上`sudo`前缀才能够访问端口，如果我们需要省略`sudo`前缀，我们就需要在系统中添加相应`.rules`文件。

### usb

首先需要创建一个`udev`配置文件，有很多方法可以配置udev，这是一个典型的设置：

```
# /etc/udev/rules.d/11-mboot-device.rules
SUBSYSTEM=="usb", ATTRS{idVendor}=="15a2", GROUP="mbootdev", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="1fc9", GROUP="mbootdev", MODE="0666"
```

该设置可以匹配所有`vid`为`0x15a2`或`0x1fc9`和`SUBSYSTEM`为`usb`的设备，注意这里的`vid`必须为小写，关于该`vid`，可以参见[usb ids](http://www.linux-usb.org/usb.ids)。

对于企业用户，如果修改了`vid`, `pid`，则需要自行根据需要添加。

使用此设置，请务必将当前用户添加到`mbootdev`组，例如：

```sh
$ sudo adduser $USER plugdev
```

创建此文件后，您需要拔出/插回设备，以便`udev`加载匹配设备的规则。执行下列命令尝试重新加载规则：

```sh
$ udevadm control --reload-rules
$ udevadm trigger
```

如果无效，你需要重启使规则生效。

### uart

对于`uart`只需将`dialout`添加至用户组:

对于`Debian/Ubuntu`，推荐使用下面语句:

```sh
sudo adduser $USER dialout
sudo adduser $USER tty  # if necessary
```

对于其它发行版:

```sh
sudo gpasswd --add ${USER} dialout
sudo gpasswd --add ${USER} tty  # if necessary
# or
sudo usermod -a -G dialout $USER
sudo usermod -a -G tty $USER    # if necessary
```

### SPI, I2C

同理，您需要在udev配置文件中添加设置，例如以下典型的设置：

```
# /etc/udev/rules.d/11-mboot-device.rules
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6001", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6011", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6010", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6014", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6015", GROUP="plugdev", MODE="0666"
```

最后，你需要执行上述`usb`一章中的操作使上述设置生效