English | [简体中文](how_to_omit_the_sudo_prefix_in_linux.zh-CN.md)

### Overview

Because `mboot` involves the interaction with the underlying device, in `Linux` we need to add `sudo` prefix in front of the command to access the port, if we need to omit `sudo` prefix, we need to add the corresponding `. rules` file in the system.

### usb

First you need to create a `udev` configuration file. There are many ways to configure udev, which is a typical config:

```
# /etc/udev/rules.d/11-mboot-device.rules
SUBSYSTEM=="usb", ATTRS{idVendor}=="15a2", GROUP="mbootdev", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="1fc9", GROUP="mbootdev", MODE="0666"
```

This setting can match all devices whose `vid` is `0x15a2` or `0x1fc9` and `SUBSYSTEM` is `usb`. Note that the `vid` must be lowercase. For the `vid`, see [usb ids](http://www.linux-usb.org/usb.ids).

For enterprise users, if you modify `vid`, `pid`, you need to add them as needed.

With this setting, be sure to add the current user to the `mbootdev` group, for example:

```sh
$ sudo adduser $USER plugdev
```

After creating this file, you need to unplug/plug in the device so that `udev` loads the rules for matching devices. Execute the following command to try to reload the rule:

```sh
$ udevadm control --reload-rules
$ udevadm trigger
```

If it doesn't work, you need to reboot to make the rule take effect.

### uart

For `uart` just add `dialout` to the user group:

For `Debian/Ubuntu`:

```sh
sudo adduser $USER dialout
sudo adduser $USER tty  # if necessary
```

For other distributions:

```sh
sudo gpasswd --add ${USER} dialout
sudo gpasswd --add ${USER} tty  # if necessary
# or
sudo usermod -a -G dialout $USER
sudo usermod -a -G tty $USER    # if necessary
```

### SPI, I2C

Similarly, you need to add settings in the `udev` configuration file, such as the following typical settings:

```
# /etc/udev/rules.d/11-mboot-device.rules
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6001", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6011", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6010", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6014", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6015", GROUP="plugdev", MODE="0666"
```

Finally, you need to perform the operations in the "usb" chapter above to make the above settings work.
