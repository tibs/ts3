#! /usr/bin/env python3

"""Transport Stream support

"""

# python-bitstring is from http://code.google.com/p/python-bitstring/
from bitstring import BitArray, BitStream

TS_PACKET_SIZE = 188

__all__ = []

def export(obj):
    if obj.__name__ not in __all__:
        __all__.append(obj.__name__)
    return obj

def export_names(names):
    if isinstance(names, basestring):
        names = [names]
    for name in names:
        if name not in __all__:
            __all__.append(name)

def _as_strings(things):
    """Pretty printing of a list

       >>> _as_strings([1])
       '1'
       >>> _as_strings([1, 2])
       '1 or 2'
       >>> _as_strings([1, 'one-and-a-half', 2])
       "1, 'one-and-a-half' or 2"
    """
    if len(things) == 1:
        return repr(things[0])
    else:
        return ', '.join(map(repr, things[:-1])) + ' or ' + repr(things[-1])

@export
class TSReadError(Exception):
    """An exception raised when an error occurs reading a TS file.

    '.filename' is the name of the file, '.data' is whatever data *was* read.

    The assumption is that this is due to a short read (normally at the end of
    the file)
    """

    def __init__(self, filename, data):
        self.filename = filename
        self.data = data

    def __str__(self):
        return "Error reading from TS file {!r}, read {} byte{} insted of {}".format(
                self.filename, len(self.data), '' if len(self.data) == 1 else 's',
                TS_PACKET_SIZE)

@export
class TSReader:
    """A class to read and/or write packets from/to a TS file.

    You may use this with 'with' - for instance::

        with TSReader(filename) as f:
            first_packet = f.read()
    """

    _mode_translations = {'r' : 'rb',
                          'w' : 'wb',
                          'x' : 'xb'}

    _mode_explanations = {'r' : 'read only',
                          'w' : 'read and write',
                          'x' : 'read and write (new file)'}

    def __init__(self, filename, mode='r'):
        """Open a TS file for reading and/or writing.

        * 'filename' is the name of the file.
        * 'mode' is one of:

          - 'r': Open the file for read only, the file must exist.
          - 'w': Open the file for read and write, creating the file if
            necessary. If the file already exists, any content is lost.
          - 'x': Open the file for read and write. The file must not exist.
        """
        self.filename = filename
        if mode not in (self._mode_translations.keys()):
            raise ValueError('Mode {} is not {}'.format(repr(mode)),
                             _as_strings(sorted(self._mode_translations.keys())))
        self.mode = mode
        self.file = open(filename, self._mode_translations[mode])

    def __str__(self):
        if self.file:
            return 'TS reader for {!r}, open for {}'.format(self.filename,
                    self._mode_explanations[self.mode])
        else:
            return 'TS reader for {!r}, closed'.format(self.filename)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.file:
            self.file.close()
            self.file = None
        if traceback:
            # An exception occurred - we don't have any extra tidying up
            # so just allow the exception to be re-raised
            return False

    def read_raw(self):
        """Read the next 188 bytes from the file, and return them.

        Returns 188 bytes, or an empty bytestring for EOF.

        If some number of bytes less than 188 is read (presumably because the
        file ends with a truncated packet), then a TSReadError will be raised,
        with the bytes read as its 'data' value.
        """
        bytes = self.file.read(TS_PACKET_SIZE)
        if len(bytes) in (0, TS_PACKET_SIZE):
            return bytes
        else:
            raise TSReadError(self.filename, bytes)

    def read(self):
        """Read the next TS packet from the file.

        Returns a TSPacket instance, or None if EOF was reached.

        If some number of bytes less than 188 is read (presumably because the
        file ends with a truncated packet), then a TSReadError will be raised,
        with the bytes read as its 'data' value.
        """
        bytes = self.file.read(TS_PACKET_SIZE)
        if len(bytes) == 0:
            return None
        elif len(bytes) == TS_PACKET_SIZE:
            return TSPacket(bytes)
        else:
            raise TSReadError(self.filename, bytes)


@export
class TSPacket:
    """A Transport Stream packet.

    """

    def __init__(self, data):
        self.data = data

if __name__ == '__main__':
    print('Hello')
    a = BitArray('0xff01')
    b = BitArray('0b110')
    print(a)
    print(b)

# vim: set tabstop=8 softtabstop=4 shiftwidth=4 expandtab: