[English](usage_example.md) | 简体中文

### MCU Boot User Interface

对比`read`和`write`命令，你可以看到在`write`命令中`address`可以被省略，所以在写入某些文件时只要输入`write <filename>`，不用担心，`mboot`将会正确的识别它，如果你不确定，你可以在任何时候使用`-h`来查看命令的帮助。

```sh
$ mboot -s 0x0403:0x6014 1000000 info
CurrentVersion:
  = 2.7.0
 AvailablePeripherals:
  - UART
  - I2C-Slave
  - SPI-Slave
  - CAN
 FlashStartAddress:
  = 0x00000000
 FlashSize:
  = 64.0 kiB
 FlashSectorSize:
  = 1.0 kiB
 FlashBlockCount:
  = 1
 AvailableCommands:
  - FlashEraseAll
  - FlashEraseRegion
  - ReadMemory
  - FillMemory
  - FlashSecurityDisable
  - ReceiveSBFile
  - Call
  - Reset
 VerifyWrites:
  = 1
 MaxPacketSize:
  = 32.0 B
 ReservedRegions:
  = 0
 RAMStartAddress:
  = 0x1FFFF800
 RAMSize:
  = 8.0 kiB
 SystemDeviceIdent:
  = 0x16240186
 FlashSecurityState:
  = Unlocked
 UniqueDeviceIdent:
  = 1163069448
 FlashFacSupport:
  = 0
 FlashAccessSegmentSize:
  = 0
 FlashAccessSegmentCount:
  = 0
 FlashReadMargin:
  = 1
 TargetVersion:
  = 1409351680

$ mboot -s 0x0403,0x6014 1000000 read 0x6000 0x20

  ADDRESS | 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F | 0123456789ABCDEF
 -----------------------------------------------------------------------------
 00006000 | 08 7C 00 20 25 84 00 00 3D 84 00 00 3F 84 00 00 | .|. %...=...?...
 00006010 | 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 | ................
 -----------------------------------------------------------------------------

$ mboot -s write 0x6000 example.bin -o 0x20
 Wrote Successfully.

$ mboot -d -s read 0x6000 0x20
INFO:root:TX-CMD: GetProperty->RAMStartAddress [ PropertyTag: 14 | memoryId = 0 ]
INFO:root:RX-CMD: RAMStartAddress = 0x1FFFF800
INFO:root:TX-CMD: GetProperty->RAMSize [ PropertyTag: 15 | memoryId = 0 ]
INFO:root:RX-CMD: RAMSize = 8.0 kiB
INFO:root:TX-CMD: GetProperty->FlashStartAddress [ PropertyTag: 3 | memoryId = 0 ]
INFO:root:RX-CMD: FlashStartAddress = 0x00000000
INFO:root:TX-CMD: GetProperty->FlashSize [ PropertyTag: 4 | memoryId = 0 ]
INFO:root:RX-CMD: FlashSize = 64.0 kiB
INFO:root:TX-CMD: ReadMemory [ StartAddr=0x00006000 | len=0x20 | memoryId=0 ]
INFO:root:RX-DATA: Successfully Received 32 Bytes

  ADDRESS | 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F | 0123456789ABCDEF
 -----------------------------------------------------------------------------
 00006000 | 80 12 46 12 46 12 46 12 46 12 46 15 24 21 64 12 | ..F.F.F.F.F.$!d.
 00006010 | 90 42 16 42 16 12 41 24 61 24 61 24 21 62 62 42 | .B.B..A$a$a$!bbB
 -----------------------------------------------------------------------------
```

### MCU Boot Original Interface

下面简单的演示以下对于内存的读写操作，请注意它们和`MCU Boot User Interface`的区别，比如输出日志的等级默认比`MCU Boot User Interface`高一级。

```sh
$ mboot -s -o read-memory 0x6000 0x20
INFO:root:TX-CMD: ReadMemory [ StartAddr=0x00006000 | len=0x20 | memoryId=0 ]
INFO:root:RX-DATA: Successfully Received 32 Bytes

  ADDRESS | 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F | 0123456789ABCDEF
 -----------------------------------------------------------------------------
 00006000 | 80 12 46 12 46 12 46 12 46 12 46 15 24 21 64 12 | ..F.F.F.F.F.$!d.
 00006010 | 90 42 16 42 16 12 41 24 61 24 61 24 21 62 62 42 | .B.B..A$a$a$!bbB
 -----------------------------------------------------------------------------

$ mboot -s -o flash-erase-region 0x6000 0x1000
INFO:root:TX-CMD: FlashEraseRegion [ StartAddr=0x00006000 | len=0x1000 | memoryId=0 ]

$ mboot -s -o write-memory 0x6000 example.bin
INFO:root:TX-CMD: WriteMemory [ StartAddr=0x00006000 | len=0x100 | memoryId=0 ]
INFO:root:TX-DATA: Successfully Send 256 Bytes

$ mboot -d -s -o read-memory 0x6000 0x20
INFO:root:TX-CMD: ReadMemory [ StartAddr=0x00006000 | len=0x20 | memoryId=0 ]
DEBUG:root:SPI-OUT-PING[2]: 5A A6
DEBUG:root:SPI-OUT-PINGR[10]: 5A A7 00 02 01 50 00 00 AA EA
DEBUG:root:TX-CMD [22]: 5A A4 10 00 5D FA 03 00 00 03 00 60 00 00 20 00 00 00 00 00 00 00
DEBUG:root:SPI-OUT-CMD[22]: 5A A4 10 00 5D FA 03 00 00 03 00 60 00 00 20 00 00 00 00 00 00 00
DEBUG:root:SPI-IN-ACK[2]: 5A A1
DEBUG:root:SPI-IN-CMD-HEAD[6]: 5A A4 0C 00 4A 52
DEBUG:root:SPI-IN-CMD-PAYLOAD[12]: A3 01 00 02 00 00 00 00 20 00 00 00
DEBUG:root:SPI-OUT-ACK[2]: 5A A1
DEBUG:root:RX-CMD [12]: A3 01 00 02 00 00 00 00 20 00 00 00
DEBUG:root:status: 0x0, value: 0x20
DEBUG:root:SPI-IN-DATA-HEAD[6]: 5A A5 20 00 1D 48
DEBUG:root:SPI-IN-DATA-PAYLOAD[32][0x0]: 08 7C 00 20 25 84 00 00 3D 84 00 00 3F 84 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
DEBUG:root:SPI-OUT-ACK[2]: 5A A1
DEBUG:root:SPI-IN-CMD-HEAD[6]: 5A A4 0C 00 0E 23
DEBUG:root:SPI-IN-CMD-PAYLOAD[12]: A0 00 00 02 00 00 00 00 03 00 00 00
DEBUG:root:SPI-OUT-ACK[2]: 5A A1
DEBUG:root:status: 0x0, value: 0x3
INFO:root:RX-DATA: Successfully Received 32 Bytes

  ADDRESS | 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F | 0123456789ABCDEF
 -----------------------------------------------------------------------------
 00006000 | 08 7C 00 20 25 84 00 00 3D 84 00 00 3F 84 00 00 | .|. %...=...?...
 00006010 | 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 | ................
 -----------------------------------------------------------------------------

```