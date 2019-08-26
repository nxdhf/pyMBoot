[English](how_to_communicate_spi_i2c.md) | 简体中文

### Overview

您可以使用FTDI设备与目标设备建立`SPI`或`I2C`连接以进行通信。请确保在此之前已正确安装`libusb`，否则您可以参考[如何安装libusb](how_to_install_libusb.zh-CN.md)

### Supported device

理论上支持以下设备：

| device  | vid,pid        |
| ------- | -------------- |
| 232     | 0x0403, 0x6001 |
| 232R    | 0x0403, 0x6001 |
| 232H    | 0x0403, 0x6014 |
| 2232    | 0x0403, 0x6010 |
| 2232D   | 0x0403, 0x6010 |
| 2232H   | 0x0403, 0x6010 |
| 4232    | 0x0403, 0x6011 |
| 4232H   | 0x0403, 0x6011 |
| 230X    | 0x0403, 0x6015 |
| FT232   | 0x0403, 0x6001 |
| FT232R  | 0x0403, 0x6001 |
| FT232H  | 0x0403, 0x6014 |
| FT2232  | 0x0403, 0x6010 |
| FT2232D | 0x0403, 0x6010 |
| FT2232H | 0x0403, 0x6010 |
| FT4232  | 0x0403, 0x6011 |
| FT4232H | 0x0403, 0x6011 |
| FT230X  | 0x0403, 0x6015 |

目前，它已经通过了`FT232H`上的测试。

### FTDI device pinout

您可以在FTDI官方网站上找到您的设备。例如[FT232H][1]，然后为您的设备下载`Datasheet.pdf`文件，您通常可以在第3章找到芯片的引脚分配。

`pyftdi`也提供了[FTDI device pinout][2]：

| [IF/1][^1] | [IF/2][^2] | UART | I2C   | SPI       | JTAG |
| ---------- | ---------- | ---- | ----- | --------- | ---- |
| `ADBUS0`   | `BDBUS0`   | TxD  | SCK   | SCLK      | TCK  |
| `ADBUS1`   | `BDBUS1`   | RxD  | SDA/O | MOSI      | TDI  |
| `ADBUS2`   | `BDBUS2`   | RTS  | SDA/I | MISO      | TDO  |
| `ADBUS3`   | `BDBUS3`   | CTS  |       | CS0       | TMS  |
| `ADBUS4`   | `BDBUS4`   |      |       | CS1/GPIO4 |      |
| `ADBUS5`   | `BDBUS5`   |      |       | CS2/GPIO5 |      |
| `ADBUS6`   | `BDBUS6`   |      |       | CS3/GPIO6 |      |
| `ADBUS7`   | `BDBUS7`   |      |       | CS4/GPIO7 |      |
| `ACBUS0`   | `BCBUS0`   |      |       | GPIO8     |      |
| `ACBUS1`   | `BCBUS1`   |      |       | GPIO9     |      |
| `ACBUS2`   | `BCBUS2`   |      |       | GPIO10    |      |
| `ACBUS3`   | `BCBUS3`   |      |       | GPIO11    |      |
| `ACBUS4`   | `BCBUS4`   |      |       | GPIO12    |      |
| `ACBUS5`   | `BCBUS5`   |      |       | GPIO13    |      |
| `ACBUS6`   | `BCBUS6`   |      |       | GPIO14    |      |
| `ACBUS7`   | `BCBUS7`   |      |       | GPIO15    |      |

请注意，FTDI引脚配置为输入或输出。由于`I2C`的`SDA`线是双向的，因此需要两个FTDI引脚来提供SDA功能，它们应连接在一起并连接到`SDA I2C`总线。应使用SCK和SDA线上的上拉电阻。您可以使用跳线帽和长排针来解决此问题。

对于`FT232H`, 它的引脚如下图所示:

| IF/1     | I2C   | SPI  |
| -------- | ----- | ---- |
| `ADBUS0` | SCK   | SCLK |
| `ADBUS1` | SDA/O | MOSI |
| `ADBUS2` | SDA/I | MISO |
| `ADBUS3` |       | CS0  |

### Connect device

根据上面的引脚排列连接器件，对于`SPI`连接，可能需要额外连接两块板子的`GND`，并且需要先为目标器件供电，然后再为FTDI器件供电。如上所述，`I2C`需要连接三条线路，这是由于FTDI设备的`MPSSE`（多协议同步串行引擎）机制。

一切准备就绪后，您可以运行`info`命令查看设备信息，如下所示。

```sh
$ mboot -s info
$ mboot -i info
```

### Some references

* [FT232H Datasheet](https://www.ftdichip.com/Support/Documents/DataSheets/ICs/DS_FT232H.pdf)

[1]:https://www.ftdichip.com/Products/ICs/FT232H.html
[2]:https://eblot.github.io/pyftdi/pinout.html

[^1]:FT4232H系列不提供16位端口(ACBUS, BCBUS)
[^2]:FT232H不支持辅助MPSSE端口，只有FT2232H和FT4232H支持。请注意，FT4232H有4个串行端口，但只有前两个接口具有MPSSE功能。
