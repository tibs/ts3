#! /usr/bin/env python3

"""Transport Stream support

"""

# python-bitstring is from http://code.google.com/p/python-bitstring/
from bitstring import ConstBitStream

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

    '.name' is the name of the file, if any, and '.data' is whatever data
    *was* read.

    The assumption is that this is due to a short read (normally at the end of
    the file)
    """

    def __init__(self, name, data):
        self.name = name
        self.data = data

    def __str__(self):
        return "Error reading from TS file {!r}, read {} byte{} insted of {}".format(
                self.name, len(self.data), '' if len(self.data) == 1 else 's',
                TS_PACKET_LEN)

@export
class TSClosedError(TSError):
    """An exception raised when an error occurs reading a closed TS file.

    '.name' is the name of the file, if any.

    For instance:

        with TSFile('somefile.ts') as f:
            p = f.read()
        p = f.read()

    ...the second 'read' will give an error, as 'f' is closed.
    """

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return "Error reading from TS file {!r}, as it is closed".format(self.name)

@export
class TS:
    """A class to read and/or write packets.

    A Transport Stream (TSStream would be silly)

    You may use this with 'with' - for instance::

        with TS(stream) as s:
            first_packet = s.read()

    although (at the moment) exiting the 'with' clause does nothing.

    You can also use it with for:

        for packet in TS(stream):
            print(packet)

    and you can filter on pids::

        g = TS(stream).pid_filter([0])
        p = next(g)

    The TSReader instance will maintain its own count of packets (as
    .num_packets_read). This plus the .initial_offset can be used to calculate
    the position of a TS packet in the stream. If the stream being used is
    not at its start, then these will only be accurate if the appropriate
    values are given when instantiating the TSReader.

    Obviously if anyone else reads/writes using the stream, or otherwise alters
    its read/write position, these will be inaccurate.
    """

    def __init__(self, stream, name='<TS stream>',
                 initial_offset=0, num_packets_already_read=0):
        """Set up a stream for TS reading or writing.

        'stream' must have a suitable 'read' method, if reading is to be done,
        and a suitable 'write' method, if writing is to be done. Suitability
        will be determined as and when the appropriate action is tried.

        'offset' may be given to indicate the byte offset in the stream.
        """
        # I find myself incorrectly trying to use TS(<filename>), so let's
        # make some attempt to catch that
        if not hasattr(stream, 'read'):
            if isinstance(stream, str):
                raise ValueError('First argument to TS, {!r}, is a string, which does not have a'
                                 ' "read" method - did you want TSFile instead?'.format(stream))
            else:
                raise ValueError('First argument to TS, {!r}, does not have a'
                                 ' "read" method'.format(stream))
        self._stream = stream
        self.name = name
        self.initial_offset = initial_offset
        self.num_packets_read = num_packets_already_read

    def __str__(self):
        return 'TS reader for {!r}'.format(self._stream)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Well, we don't know that we've got anything to do
        if traceback:
            # An exception occurred - we don't have any extra tidying up
            # so just allow the exception to be re-raised
            return False

    def _read(self):
        """Read the next TS packet from the stream.

        Returns a byte array, or None if EOF was found.

        If some number of bytes less than 188 is read (presumably because the
        file ends with a truncated packet), then a TSReadError will be raised,
        with the bytes read as its 'data' value.
        """
        if self._stream is None:
            raise TSClosedError(self.name)
        buffer = self._stream.read(TS_PACKET_LEN)
        if len(buffer) == 0:
            return None
        elif len(buffer) == TS_PACKET_LEN:
            self.num_packets_read += 1
            return buffer
        else:
            raise TSReadError(self.name, buffer)

    def read(self):
        """Read the next TS packet from the stream.

        Returns a TSPacket instance, or None if EOF was reached.

        If some number of bytes less than 188 is read (presumably because the
        file ends with a truncated packet), then a TSReadError will be raised,
        with the bytes read as its 'data' value.
        """
        buffer = self._read()
        if buffer is None:
            return None
        else:
            # The packet index (stored on the TSPacket) starts at 0
            packet_index = self.num_packets_read - 1
            packet = TSPacket(buffer,
                              packet_index,
                              packet_index*TS_PACKET_LEN + self.initial_offset)
            return packet

    def __iter__(self):
        """Our default iterator returns all TS packets.
        """
        while True:
            next_packet = self.read()
            if next_packet:
                yield next_packet
            else:
                return

    def pid_filter(self, pids):
        """An iterator that returns only TS packets with the selected pids.

        'pids' should be a sequence of PIDs (something that one can use 'in'
        on).
        """
        while True:
            buffer = self._read()
            if buffer is None:
                return
            else:
                pid = ((buffer[1] & 0x1F) << 8) | buffer[2]
                if pid in pids:
                    # The packet index (stored on the TSPacket) starts at 0
                    packet_index = self.num_packets_read - 1
                    packet = TSPacket(buffer,
                                      packet_index,
                                      packet_index*TS_PACKET_LEN + self.initial_offset)
                    yield packet


@export
class TSFile(TS):
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
            raise ValueError('Mode {} is not {}'.format(repr(mode),
                             _as_strings(sorted(self._mode_translations.keys()))))
        stream = open(filename, self._mode_translations[mode])
        super().__init__(stream, filename)
        self.mode = mode

    def __str__(self):
        if self._stream:
            return 'TS reader for {!r}, open for {}'.format(self.name,
                    self._mode_explanations[self.mode])
        else:
            return 'TS reader for {!r}, closed'.format(self.name)

    def close(self):
        if self._stream:
            self._stream.close()
            self._stream = None

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        if traceback:
            # An exception occurred - we don't have any extra tidying up
            # so just allow the exception to be re-raised
            return False

class ValidatingConstBitStream(ConstBitStream):

    def read_const(self, size, name, required_value):
        val = self.read(size)
        if val.uint != required_value:
            print(type(val), val)
            print(type(required_value), required_value)
            print(val == required_value)
            raise ValueError('Value {!r} of size {} is {} instead of {:#x}'.format(name,
                             size, val, required_value))
        return val

    def read_reserved(self, size, name):
        val = self.read(size)
        b = Bits(val, length=size)
        if not b.all():
            raise ValueError('Value {!r} of size {} is {} but should be all bits set'.format(name,
                             size, val))

    def read_range(self, size, name, min, max):
        val = self.read(size)
        if not (min <= val.uint <= max):
            raise ValueError('Value {!r} of size {} is {} instead of {:#x}..{:#x}'.format(name,
                             size, val, min, max))
        return val

class ForgivingConstBitStream(ConstBitStream):

    def read_const(self, size, name, required_value):
        return self.read(size)

    def read_range(self, size, name, min, max):
        return self.read(size)

    def read_reserved(self, size, name):
        return self.read(size)

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

    def __init__(self, buffer, index=None, offset=None, validating=False):
        self.buffer = buffer
        self.offset = offset
        self.index = index
        self.validating = validating
        # It's not a TS packet if it doesn't start with 0x47
        if buffer[0] != 0x47:
            raise TSError('First byte of TS packet is {:#02x}, not 0x47'.format(buffer[0]))
        # And the length is well defined
        if len(buffer) != TS_PACKET_LEN:
            raise TSError('TS packet is {} bytes long, not {}'.format(len(buffer), TS_PACKET_LEN))
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
        buffer = self.buffer[3:]
        for val in buffer[:11]:
            words.append('{:02x}'.format(val))
        if len(buffer) > 11:
            words.append('...')
        return ' '.join(words)

    def __repr__(self):
        return 'TSPacket("%s")'%_hexify_array(self.buffer)

    def __eq__(self, other):
        return self.buffer == other.buffer

    def __ne__(self, other):
        return self.buffer != other.buffer

    def _split(self):
        if self.validating:
            bits = ValidatingConstBitStream(self.buffer)
        else:
            bits = ForgivingConstBitStream(self.buffer)

        print(bits)

        sync_byte = bits.read_const(8, 'sync_byte', 0x47) # or I could use an offset to ignore this...
        transport_error_indicator = bits.read(1)
        payload_unit_start_indicator = bits.read(1)
        transport_priority = bits.read(1)
        pid = bits.read(13)
        transport_scrambling_control = bits.read(2)
        adaptation_field_control = bits.read(2)
        continuity_counter = bits.read(4)

        print(sync_byte, transport_error_indicator, payload_unit_start_indicator,
              transport_priority, pid, transport_scrambling_control,
              adaptation_field_control, continuity_counter)

        if adaptation_field_control in (0b10, 0b11):
            self.adapt = self._read_adaptation_field(bits)

        if adaptation_field_control in (0b01, 0b11):
            self.data = self._read_data_bytes(bits)

        if self.validating:
            # check that we don't have anything left
            pass

    def _read_adaptation_field(self, bits):
        adaptation_field_length = bits.read(8)
        if adaptation_field_length == 0:
            return None             # is this the best thing to do?
        discontinuity_indicator = bits.read(1)
        random_access_indicator = bits.read(1)
        elementary_stream_priority_indicator = bits.read(1)
        PCR_flag = bits.read(1)
        OPCR_flag = bits.read(1)
        splicing_point_flag = bits.read(1)
        transport_private_data_flag = bits.read(1)
        adaptation_field_extension_flag = bits.read(1)
        if PCR_flag:
            program_clock_reference_base = bits.read(33)
            reserved = bits.read_reserved(6, 'Reserved, after program_clock_reference_base')
            program_clock_reference_extension = bits.read(9)

    def _read_data_bytes(self, bits):
        pass

if __name__ == '__main__':
    print('Hello')

# vim: set tabstop=8 softtabstop=4 shiftwidth=4 expandtab:
