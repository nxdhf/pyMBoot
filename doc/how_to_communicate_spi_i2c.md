English | [简体中文](how_to_communicate_spi_i2c.zh-CN.md)

### Overview

You can use an FTDI device to make an `SPI` or `I2C` connection to your target device for spi communication. Please make sure that `libusb` has been installed correctly before this， otherwise you can refer to [How to install libusb](how_to_install_libusb.md)

### Supported device

Theoretically support the following equipment:

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

At present, it has passed the test on `FT232H`.

### FTDI device pinout

You can find you device on the FTDI official website. such as [FT232H][1], then download `Datasheet.pdf` for you device, You can usually find the pinout of the chip in Chapter 3.

`pyftdi` also provide [FTDI device pinout][2]:

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

Note that FTDI pins are either configured as input or output. As `I2C` SDA line is bi-directional, two FTDI pins are required to provide the SDA feature, and they should be connected together and to the SDA I2C bus line. Pull-up resistors on SCK and SDA lines should be used. You can use a jumper cap and a pin header connector to solve this problem.

For `FT232H`, its pinout is as follows:

| IF/1     | I2C   | SPI  |
| -------- | ----- | ---- |
| `ADBUS0` | SCK   | SCLK |
| `ADBUS1` | SDA/O | MOSI |
| `ADBUS2` | SDA/I | MISO |
| `ADBUS3` |       | CS0  |

### Connect device

Connect the device according to the pinout above, additional connection to GND may be required if `SPI` communication is performed, and you need to power the target device first, then your FTDI device. `I2C` needs to connect three wires, as mentioned above, because of the `MPSSE`(Multi-Protocol Synchronous Serial Engine) mechanism of FTDI devices.

When everything is ready, you can run `info` command to view device information as follows.

```sh
$ mboot -s info
$ mboot -i info
```

### Some references

* [FT232H Datasheet](https://www.ftdichip.com/Support/Documents/DataSheets/ICs/DS_FT232H.pdf)

[1]:https://www.ftdichip.com/Products/ICs/FT232H.html
[2]:https://eblot.github.io/pyftdi/pinout.html

[^1]:16-bit port (ACBUS, BCBUS) is not available with FT4232H series
[^2]:FT232H does not support a secondary MPSSE port, only FT2232H and FT4232H do. Note that FT4232H has 4 serial ports, but only the first two interfaces are MPSSE-capable.