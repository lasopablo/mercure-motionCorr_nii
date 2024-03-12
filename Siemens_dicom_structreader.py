''' Stream-like reader for packed data '''

from struct import Struct

_ENDIAN_CODES = '@=<>!'

class Unpacker(object):
    def __init__(self, buf, ptr=0, endian=None):
        self.buf = buf
        self.ptr = ptr
        self.endian = endian
        self._cache = {}

    def unpack(self, fmt):
        pkst = self._cache.get(fmt)
        if pkst is None:  # struct not in cache
            if self.endian is None or fmt[0] in _ENDIAN_CODES:
                pkst = Struct(fmt)
            else:  # we're going to modify the endianness with our
                # default.
                endian_fmt = self.endian + fmt
                pkst = Struct(endian_fmt)
                self._cache[endian_fmt] = pkst
            self._cache[fmt] = pkst
        values = pkst.unpack_from(self.buf, self.ptr)
        self.ptr += pkst.size
        return values

    def read(self, n_bytes=-1):
        start = self.ptr
        if n_bytes == -1:
            end = len(self.buf)
        else:
            end = start + n_bytes
        self.ptr = end
        return self.buf[start:end]

    def nt_str(self, s):
        zero_pos = s.find(b'\x00')
        if zero_pos == -1:
            return s
        return s[:zero_pos].decode('latin-1')

    def csaread(self, csa_str):
        _CONVERTERS = {
        'FL': float,  # float
        'FD': float,  # double
        'DS': float,  # decimal string
        'SS': int,    # signed short
        'US': int,    # unsigned short
        'SL': int,    # signed long
        'UL': int,    # unsigned long
        'IS': int,    # integer string
        }

        self.buf = csa_str
        csa_len = len(csa_str)
        csa_dict = {'tags': {}}
        hdr_id = csa_str[:4]
        if hdr_id == b'SV10':  # CSA2
            hdr_type = 2
            self.ptr = 4  # omit the SV10
            csa_dict['unused0'] = self.read(4)
        else:  # CSA1
            hdr_type = 1
        csa_dict['type'] = hdr_type
        csa_dict['n_tags'], csa_dict['check'] = self.unpack('2I')
        for tag_no in range(csa_dict['n_tags']):
            name, vm, vr, syngodt, n_items, last3 = \
                self.unpack('64si4s3i')
            vr = self.nt_str(vr)
            name = self.nt_str(name)
            tag = {'n_items': n_items,
                'vm': vm,  # value multiplicity
                'vr': vr,  # value representation
                'syngodt': syngodt,
                'last3': last3,
                'tag_no': tag_no}
            if vm == 0:
                n_values = n_items
            else:
                n_values = vm
            # data converter
            converter = _CONVERTERS.get(vr)
            # CSA1 specific length modifier
            if tag_no == 1:
                tag0_n_items = n_items
            items = []
            for item_no in range(n_items):
                x0, x1, x2, x3 = self.unpack('4i')
                ptr = self.ptr
                if hdr_type == 1:  # CSA1 - odd length calculation
                    item_len = x0 - tag0_n_items
                    if item_len < 0 or (ptr + item_len) > csa_len:
                        if item_no < vm:
                            items.append('')
                        break
                else:  # CSA2
                    item_len = x1
                if item_no >= n_values:
                    assert item_len == 0
                    continue
                item = self.nt_str(self.read(item_len))
                if converter:
                    if item_len == 0:
                        n_values = item_no
                        continue
                    item = converter(item)
                items.append(item)
                plus4 = item_len % 4
                if plus4 != 0:
                    self.ptr += (4 - plus4)
            tag['items'] = items
            csa_dict['tags'][name] = tag
        return csa_dict