[English](usage_problem.md) | 简体中文

### 执行`pip install`时出现`TypeError`错误？

如果出现“TypeError: 'encoding' is an invalid keyword argument for this function”，请确保你使用的是`pip3`，如果它没有安装，在`ubuntu`上你可以使用以下命令安装：

```sh
$ sudo apt update
$ sudo apt install python3-pip
```

`windows`下会自动安装当前python版本对应的`pip`，不用安装。

### 安装成功但运行时命令行提示没有找到mboot命令？

因为`linux/macOS`的权限问题，如果你没有使用`sudo`安装，它会被安装到用户目录，请检查你的`$PATH`，你可以手动通过下面的命令添加用户目录：

```sh
$ export PATH=$PATH:~/.local/bin
# If you need to open bash the next time it still works, you need to modify ~/.bashrc and add the above command at the end.
$ vi ~/.bashrc  # if you use zsh, modify ~/.zshrc
# Configuration takes effect immediately
$ source ~/.bachrc
```
windows下通常会全局安装，如果没有，请在`PATH`中添加用户目录，例如`C:\Users\Username\AppData\Roaming\Python36\Scripts`。

### 设备出错如何调试？

使用`-d`选项你可以看到运行过程中执行了那些命令，而使用`-d 2`选项你可以看到总线上具体发送的数据，重启设备以避免上一个错误的影响，尤其对于`uart`设备来说。 

### 我插入了设备，但mboot提示“设备搜索失败”？

您可以尝试手动指定`vid`, `pid`或相应的`serial number`。请注意，如果是`uart`设备，它的自动搜索是基于`vid`, `pid`的，因此如果您的设备的`vid`, `pid`不在列表中，就找不到它，您可以提交一个`issues`，附上你设备的`vid`, `pid`。

### 能否同时插入两个具有相同`vid, pid`的设备？

对于`uart`来说，这是可以的，因为自动搜索后会记录下用户选择设备的串口号，这是不会重复的，但对于其它外设来说，这是不行的，虽然仍然会弹出外设选择，但因为记录的是`vid, pid`，所以最终打开的设备会是第一个被发现的设备。

### 为什么不使用`click`？

该工具用于嵌入式系统，我认为它的命令行界面应该是高效的，这意味着它命令的参数应该是一致的，位置参数可以省略。例如`read`命令中的`address`和`write`命令，在`write`命令中，`address`在某些条件下可以省略，所以原项目不得不将它定义为选项`-a` ，但在`read`命令中，它又是必须分配的位置参数。什么时候需要指定`-a`而什么时候不需要，这很容易混淆。总之，我的一些看法和[Karol Kuczmarski的][1]的一致，“click”是一个很好的库，但不应该使用在这里。

[1]:http://xion.io/post/programming/python-dont-use-click.html
