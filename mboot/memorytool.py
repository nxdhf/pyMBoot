import collections

class MemoryBlock(object):
    def __init__(self, start, end=None, length=None):
        self.start = start
        if end or length:
            self.end = self.start + length if length else end
            self.length = end - self.start if end else length
        else:
            raise ValueError('Must inter end or length.')
        
    @classmethod
    def from_sequence(cls, sequence):
        if isinstance(sequence, collections.Sequence):
            try:    # input may be is an str
                start, end = sequence
            except ValueError as e:
                raise TypeError('The parameter requires a list or tuple, such as [start, end]')
        else:
            raise TypeError('The parameter requires a list or tuple, not {}'.format(type(sequence)))
        return cls(start, end)
    
    def __len__(self):
        return self.length

    def __str__(self):
        return '{} start:{:#010x} end:{:#010x} length: {:#010x} @{}'.format(self.__class__.__name__,
            self.start, self.end, self.length, id(self))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return other.start == self.start and other.end == self.end

    def __contains__(self, other):
        if isinstance(other, collections.Sequence):
            _other = self.from_sequence(other)
        elif isinstance(other, MemoryBlock):
            _other = other  # prevent rewriting other
        else:
            raise TypeError('The parameter requires a list, tuple or {}, such as [start, end]'.format(
                    self.__class__.__name__))
        
        return _other.start >= self.start and _other.end <= self.end

    def __sub__(self, other):
        """
        """
        if isinstance(other, collections.Sequence):
            _other = self.from_sequence(other)
        elif isinstance(other, self.__class__):
            _other = other  # prevent rewriting other
        else:
            raise TypeError('The parameter requires a list, tuple or {}, such as [start, end]'.format(
                    self.__class__.__name__))

        block_list = []
        if self.start > _other.end or self.end < _other.start:
            return [self]
        elif self.start < _other.start <= self.end:
            block_list.append(self.__class__(self.start, _other.start))
            if self.end > _other.end:
                block_list.append(self.__class__(_other.end, self.end))
        elif self.start <= _other.end < self.end:
            if self.start < _other.start:
                block_list.append(self.__class__(self.start, _other.start))
            block_list.append(self.__class__(_other.end, self.end))
        return block_list


class Memory(MemoryBlock):
    pass

class Flash(MemoryBlock):
    def __init__(self, start, end=None, length=None, sector_size=0x1000):
        super().__init__(start, end, length)
        self.sector_size = sector_size

    @staticmethod
    def align_up(number, base):
        return ((number + base -1) & (~(base-1)))

    @staticmethod
    def align_down(number, base):
        return (number & (~(base-1)))

if __name__ == "__main__":
    x = MemoryBlock(*[0,100])

    y = MemoryBlock(*[50,90])
    print('{!r} {!r}'.format(x,y))
    print(y in x)
    print((x-y)[0])
    print((x-y)[1])
    print(x,y)

    z = Flash(*[0,0x1000])
    print(z, hex(z.sector_size))


