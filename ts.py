#! /usr/bin/env python3

"""Transport Stream support

"""

# python-bitstring is from http://code.google.com/p/python-bitstring/
from bitstring import BitArray, BitStream

TS_PACKET_LEN = 188

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

def _hexify_array(bytes):
    """Return a representation of an array of bytes as a hex values string.
    """
    words = []
    for val in bytes:
        words.append('{:#02x}'.format(val))
    return ''.join(words)

@export
class TSError(Exception):
    pass

@export
class TSReadError(TSError):
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
                TS_PACKET_LEN)

@export
class TSReader:
    """A class to read and/or write packets.

    You may use this with 'with' - for instance::

        with TSReader(stream) as f:
            first_packet = f.read()

    although (at the moment) exiting the 'with' clause does nothing.

    The TSReader instance will maintain its own count of packets (as
    .packet_count). This plus the .initial_offset can be used to calculate
    the position of a TS packet in the stream. If the stream being used is
    not at its start, then these will only be accurate if the appropriate
    values are given when instantiating the TSReader.

    Obviously if anyone else reads/writes using the stream, or otherwise alters
    its read/write position, these will be inaccurate.
    """

    def __init__(self, stream, offset=0, count=0):
        """Set up a stream for TS reading or writing.

        'stream' must have a suitable 'read' method, if reading is to be done,
        and a suitable 'write' method, if writing is to be done. Suitability
        will be determined as and when the appropriate action is tried.

        'offset' may be given to indicate the byte offset in the stream.
        """
        self.stream = stream
        self.initial_offset = offset
        self.packet_count = count

    def __str__(self):
        return 'TS reader for {!r}'.format(self.stream)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Well, we don't know that we've got anything to do
        if traceback:
            # An exception occurred - we don't have any extra tidying up
            # so just allow the exception to be re-raised
            return False

    def read(self):
        """Read the next TS packet from the stream.

        Returns a TSPacket instance, or None if EOF was reached.

        If some number of bytes less than 188 is read (presumably because the
        file ends with a truncated packet), then a TSReadError will be raised,
        with the bytes read as its 'data' value.
        """
        bytes = self.stream.read(TS_PACKET_LEN)
        if len(bytes) == 0:
            return None
        elif len(bytes) == TS_PACKET_LEN:
            # The packet index (stored on the TSPacket) starts at 0
            packet = TSPacket(bytes, self.packet_count,
                              self.packet_count*TS_PACKET_LEN+self.initial_offset)
            self.packet_count += 1
            return packet
        else:
            raise TSReadError(self.filename, bytes)

@export
class TSFileReader(TSReader):
    """A class to read and/or write packets from/to a TS file.

    You may use this with 'with' - for instance::

        with TSReader(filename) as f:
            first_packet = f.read()

    Exiting the 'with' clause will close the file.
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
        if mode not in (self._mode_translations.keys()):
            raise ValueError('Mode {} is not {}'.format(repr(mode)),
                             _as_strings(sorted(self._mode_translations.keys())))
        self.filename = filename
        self.mode = mode
        stream = open(filename, self._mode_translations[mode])
        super().__init__(stream, offset=0, count=0)

    def __str__(self):
        if self.file:
            return 'TS reader for {!r}, open for {}'.format(self.filename,
                    self._mode_explanations[self.mode])
        else:
            return 'TS reader for {!r}, closed'.format(self.filename)

    def __exit__(self, exc_type, exc_value, traceback):
        if self.file:
            self.file.close()
            self.file = None
        if traceback:
            # An exception occurred - we don't have any extra tidying up
            # so just allow the exception to be re-raised
            return False


@export
class TSPacket:
    """A Transport Stream packet.
    """

    # The following are lazily calculated if necessary
    _already_split = None
    _pusi = None
    _adapt = None
    _payload = None

    # Ditto with looking for a PCR
    _checked_for_pcr = False
    _pcr = None

    def __init__(self, buffer, index=None, offset=None):
        self.data = buffer
        self.offset = offset
        self.index = index
        # It's not a TS packet if it doesn't start with 0x47
        if buffer[0] != 0x47:
            raise TSError('First byte of TS packet is {:#02x}, not 0x47'%(buffer[0]))
        # And the length is well defined
        if len(buffer) != TS_PACKET_LEN:
            raise TSError('TS packet is %d bytes long, not %d'%(len(buffer), TS_PACKET_LEN))
        # The PID is useful to know early on, and fairly easy to work out
        self.pid = ((buffer[1] & 0x1F) << 8) | buffer[2]

    def is_padding(self):
        return self.pid == 0x1fff

    def __str__(self):
        #self._split()
        words = []
        words.append('TS packet PID {:04x}'.format(self.pid))
        #if self.pusi:
        #    words.append('[pusi]')
        #if self.adapt and self.payload:
        #    words.apend('A+P')
        #elif self.adapt:
        #    words.append('A')
        #elif self.payload:
        #    words.append('P')
        data = self.data[3:]
        for val in data[:11]:
            words.append('{:02x}'.format(val))
        if len(data) > 11:
            words.append('...')
        return ' '.join(words)

    def __repr__(self):
        return 'TSPacket("%s")'%_hexify_array(self.data)

    def __eq__(self, other):
        return self.data == other.data

    def __ne__(self, other):
        return self.data != other.data

if __name__ == '__main__':
    print('Hello')
    a = BitArray('0xff01')
    b = BitArray('0b110')
    print(a)
    print(b)

# vim: set tabstop=8 softtabstop=4 shiftwidth=4 expandtab:
