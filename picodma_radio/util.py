def dump_hex(x):
    print("".join("\\x%02x" % i for i in x))

def dump_hex_pretty(buf):
    ascii_parts = bytearray(16)

    for i in range(0, len(buf)):
        if buf[i] > 32 and buf[i] < 127:
            ascii_parts[i % len(ascii_parts)] = buf[i]
        else:
            ascii_parts[i % len(ascii_parts)] = ord('.')

        print('%02x' % buf[i], end=' ')
        if i != 0 and not (i + 1) % 8:
            print(' ', end='')
        if i != 0 and not (i + 1) % 16:
            print(' %s' % ''.join(map(chr, ascii_parts)))
