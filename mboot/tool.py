def crc16(data, crc=0, poly=0x1021):
    '''Default calculate CRC-16/XMODEM
    width:      16
    polynomial: 0x1021
    init value: 0x0000
    xor out:    0x0000
    reflect in false
    reflect out false
    '''
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            temp = crc << 1
            if crc & 0x8000:
                temp ^= poly
            crc = temp
    return hex(crc & 0xFFFF)

if __name__ == '__main__':
    data = bytes.fromhex('5A A4 0C 00 07 00 00 02 01 00 00 00 00 00 00 00')
    # import array
    # data = array.array('B', data)
    result = crc16(data)

    print('data:{}\nresult:{}'.format(data, result))
