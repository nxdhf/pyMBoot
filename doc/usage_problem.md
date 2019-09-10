English | [简体中文](usage_problem.zh-CN.md)

### TypeError error when executing pip install?

if "TypeError: 'encoding' is an invalid keyword argument for this function" occurs, make sure that you are currently using pip3. If it is not installed, on ubuntu, you can use the following command to install it.

```sh
$ sudo apt update
$ sudo apt install python3-pip
```

the `pip` corresponding to the current Python version will be installed automatically under `Windows` without manual installation.

### Installation was successful but the CLI prompt mboot command was not found?

Because of the `Linux/macOS` privilege problem, if you do not use `sudo` installation permissions, it will be installed to the user directory, please check your `$PATH`, you can manually add the user directory through the following command.

```sh
$ export PATH=$PATH:~/.local/bin
# If you need to open bash the next time it still works, you need to modify ~/.bashrc and add the above command at the end.
$ vi ~/.bashrc  # if you use zsh, modify ~/.zshrc
# Configuration takes effect immediately
$ source ~/.bachrc
```

Usually under windows, it is installed globally. If not, add a user directory to `PATH`, such as `C:\Users\Username\AppData\Roaming\Python36\Scripts`.

### "[Errno 13] xxx denied" error

Common mistakes are as follows:

* [Errno 13] Access denied (insufficient permissions)
* [Errno 13] Permission denied: '/dev/ttyACM0'

This is caused by insufficient permissions. For details, please refer to [how to omit the sudo prefix in linux](how_to_omit_the_sudo_prefix_in_linux.md)

### How to debug the device error?

Using the `-d` option you can see which commands were executed during the run, and with the `-d 2` option you can see the specific data sent on the bus. Reboot the device to avoid the effects of the previous error, especially for `Uart` device.

### I inserted the device but mboot prompt "device search failed"?

You can try to manually specify `vid`, `pid` or the corresponding `serial number`. Note that even if it is `uart`, its automatic search is based on `vid`, `pid`, so if your device's `vid`, `pid` is not in the list, it will not be found, you can open a `issues` with you device `vid`, `pid`.

### Can I insert multiple devices with the same `vid, pid` at the same time?

For `uart`, this problem does not exist, because the serial number of the device selected by the user will be recorded after the automatic search, which will not be repeated. For other peripherals, `mboot` supports multiple insertion of the device. It will pop up the peripheral selection prompt, then you can select the appropriate device, and you can manually specify the details of the device. See [insert multiple devices with the same vid pid](insert_multiple_devices_with_the_same_vid_pid.md) in detail.

### Reading and writing the serial port in Linux sometimes makes mistakes, but the windows are normal？

The following two errors will occur, along with some mboot read and write errors.

* ERROR: read failed: device reports readiness to read but returned no data (device disconnected or multiple access on port?)
* ERROR: Attempting to use a port that is not open

After the device is inserted into the device, it runs normally. However, after about 1~2 seconds, an error occurs. Waiting for the system to mount and save, it returns to normal. I suspect that it is a issue when mounting the device.

This issue seems to be a problem with the `kernel` version. see [1](https://bugs.launchpad.net/ubuntu/+source/linux-lts-trusty/+bug/1501345)[2](https://bugs.launchpad.net/ubuntu/+source/python2.7/+bug/1501240)

### Why not use `click`?

this tool is used in embedded systems, I think its CLI should be efficient, which means that the parameters of its commands should be consistent and the positional parameters can be omitted. Such as the `address` in the `read` command and the `write` command, in `write` command, `address` can be omitted under certain conditions, so the original project has to define it as an option `-a`, but in `read` command it is a positional parameter that must be assigned. when `-a` is required and when `-a` is not required, which is easily confusing. In conclusion, some of my views are in line with [Karol Kuczmarski's][1], `click` is a good library, but it shouldn't be used here.


[1]:http://xion.io/post/programming/python-dont-use-click.html
