from enum import Enum

class Interface(int, Enum):
    UART    = 1
    I2C     = 2
    SPI     = 3
    CAN     = 4
    USB     = 5

class KeyOperation(int, Enum):
    enroll                  = 0
    set_user_key            = 1
    set_key                 = 2
    write_key_nonvolatile   = 3
    read_key_nonvolatile    = 4
    write_key_store         = 5
    read_key_store          = 6