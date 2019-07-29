from enum import Enum

class Interface(int, Enum):
    UART    = 0
    I2C     = 1
    SPI     = 2
    CAN     = 3
    USB     = 4

class KeyOperation(int, Enum):
    enroll                  = 0
    set_user_key            = 1
    set_key                 = 2
    write_key_nonvolatile   = 3
    read_key_nonvolatile    = 4
    write_key_store         = 5
    read_key_store          = 6