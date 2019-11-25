import logging
import time

from struct import unpack_from

from .spi import *

logger = logging.getLogger('picodma_radio.spi_util')

def search_bytes16(start_addr, window_size, value):
    spi_search_function = dma_search16

    return search_bytes_spi(start_addr, window_size, value, spi_search_function)


def search_bytes32(start_addr, window_size, byte_array):
    spi_search_function = dma_search32

    return search_bytes_spi(start_addr, window_size, value, spi_search_function)


def search_bytes_spi(addr, window_size, value, spi_search_function):
    spi_search_function(addr, window_size, value)
    time.sleep(.1)

    if dma_search_busy() == 1:
        logging.debug('searching... : address %d, length %d' % (addr, window_size))
        time.sleep(.5)

        while dma_search_busy() == 1:
            logging.debug('searching... : address %d, length %d (is length reasonable?)' % (addr, window_size))
            time.sleep(2)

    if dma_search_has_failed() == 1:
        logging.debug('search_bytes failed: address %d, length %d' % (addr, window_size))

    matches = dma_search_length()

    if matches > 0:
       return True, next(dma_search_results(addr))

    return False, None, None

# fpga read size is 4*512
block_size = 512 * 4

# pad_zeros will return null bytes in regions where reads consistently fail
# this is OK in some applications, but dangerous in others
def read_pa(paddr, count, result_buf, pad_zeros=True):
    blocks = int(count / block_size)
    remainder = count % block_size
    block_buf = memoryview(bytearray(block_size + 2))

    for i in range(0, blocks):
        dma_async_read(paddr + i * block_size)
        if dma_read_has_failed() == 1:
            logging.debug('read_pa failed at %x' % current_addr)
        count_read = dma_read_length()
        if count_read < block_size:
            logging.debug('read_pa failed to read full block at %x' % current_addr)

        block = dma_read_buffer()
        if block:
            result_buf[i * block_size:i * block_size + len(block)] = block
        elif pad_zeros:
            pass # result_buf is null initialized, failed read skips this region
        else: # hard fail
            return False

    if remainder:
        dma_async_read(paddr + blocks * block_size)
        if dma_read_has_failed() == 1:
            logging.debug('read_pa failed at %x' % current_addr)
        count_read = dma_read_length()
        if count_read < block_size:
            logging.debug('read_pa failed to read full block at %x' % current_addr)

        block = dma_read_buffer()
        if block:
            result_buf[blocks * block_size:] = block[:remainder]
        elif pad_zeros:
            pass # result_buf is null initialized, failed read skips this region
        else: # hard fail
            return False

    return True

def write_pa(paddr, data):
    if len(data) % 8 != 0:
        logger.error("trying to write incomplete buffer (%d bytes) to 0x%x" % (len(data), paddr))
        return False

    if paddr % 8 != 0:
        logger.error("trying to write data to non word-aligned address 0x%x" % paddr)
        return False

    for i in range(0, len(data), 8):
        next_bytes = data[i: i + 8]
        dma_write(paddr + i, struct.pack("<Q", next_bytes))

    return True
