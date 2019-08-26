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

### How to debug the device error?

Using the `-d` option you can see which commands were executed during the run, and with the `-d 2` option you can see the specific data sent on the bus. Reboot the device to avoid the effects of the previous error, especially for `Uart` device.

### I inserted the device but mboot prompt "device search failed"?

You can try to manually specify `vid`, `pid` or the corresponding `serial number`. Note that even if it is `uart`, its automatic search is based on `vid`, `pid`, so if your device's `vid`, `pid` is not in the list, it will not be found, you can open a `issues` with you device `vid`, `pid`.

### Can I insert two devices with the same `vid, pid` at the same time?

For `uart`, this is ok, because the serial number of the user-selected device will be recorded after the automatic search，which will not be repeated, but for other peripherals, this will not work, although the peripheral selection will still pop up, but because the record is `vid, pid`, the device that is finally opened will be the first device to be discovered.s

### Why not use `click`?

this tool is used in embedded systems, I think its CLI should be efficient, which means that the parameters of its commands should be consistent and the positional parameters can be omitted. Such as the `address` in the `read` command and the `write` command, in `write` command, `address` can be omitted under certain conditions, so the original project has to define it as an option `-a`, but in `read` command it is a positional parameter that must be assigned. when `-a` is required and when `-a` is not required, which is easily confusing. In conclusion, some of my views are in line with [Karol Kuczmarski's][1], `click` is a good library, but it shouldn't be used here.


[1]:http://xion.io/post/programming/python-dont-use-click.html
