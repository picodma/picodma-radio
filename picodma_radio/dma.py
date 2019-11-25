import logging

from .spi_util import read_pa, write_pa, search_bytes16 as spi_search_bytes16, search_bytes32 as spi_search_bytes32


logger = logging.getLogger('picodma_radio.dma')

NETWORK_BLOCK_SIZE = 0x1000

class spi_dma(object):
    def __init__(self):
        pass

    # returns None if read failed (and we're not padding)
    def read_pa(self, paddr, count, pad_zeros=True, result_buf=None):
        if not result_buf:
            result_buf = bytearray(count)

        success_status = read_pa(paddr, count, result_buf, pad_zeros)

        if success_status:
            return result_buf
        else:
            logger.error('failed to read %d bytes at 0x%x' % (count, paddr))
            return None

    def read_pa_stream(self, sock, paddr, count, pad_zeros=True):
        result_buf = memoryview(bytearray(NETWORK_BLOCK_SIZE))

        blocks = int(count / NETWORK_BLOCK_SIZE)
        remainder = count % NETWORK_BLOCK_SIZE

        for block_num in range(0, blocks):
            read_status = self.read_pa(paddr + block_num * NETWORK_BLOCK_SIZE, NETWORK_BLOCK_SIZE, pad_zeros, result_buf)
            if read_status:
                sock.send(result_buf)
            else:
                logger.error('failed to read %d bytes at 0x%x' % (NETWORK_BLOCK_SIZE, paddr + block_num * NETWORK_BLOCK_SIZE))
                return False

        if remainder:
            result_buf = result_buf[:remainder]
            read_status = self.read_pa(paddr + blocks * NETWORK_BLOCK_SIZE, remainder, pad_zeros, result_buf)
            if read_status:
                sock.send(result_buf)
            else:
                logger.error('failed to read %d bytes at 0x%x' % (remainder, paddr + blocks * NETWORK_BLOCK_SIZE))
                return False

        return True

    def write_pa_stream(self, sock, paddr, count, pad_zeros=True):
        write_buf = memoryview(bytearray(NETWORK_BLOCK_SIZE))

        blocks = int(count / NETWORK_BLOCK_SIZE)
        remainder = count % NETWORK_BLOCK_SIZE

        for block_num in range(0, blocks):
            recv_into_blocking(sock, write_buf, NETWORK_BLOCK_SIZE)

            write_status = self.write_pa(paddr + block_num * NETWORK_BLOCK_SIZE, write_buf)
            if not write_status:
                logger.error('failed to write %d bytes at 0x%x' % (NETWORK_BLOCK_SIZE, paddr + block_num * NETWORK_BLOCK_SIZE))
                return False

        if remainder:
            write_buf = write_buf[:remainder]
            recv_into_blocking(sock, write_buf, remainder)

            write_status = self.write_pa(paddr + block_num * NETWORK_BLOCK_SIZE, write_buf)
            if not write_status:
                logger.error('failed to write %d bytes at 0x%x' % (NETWORK_BLOCK_SIZE, paddr + blocks * NETWORK_BLOCK_SIZE))
                return False

        return True

    def write_pa(self, paddr, data):
        success_status = write_pa(paddr, data)

        if not success_status:
            logger.error('failed to write %d bytes at 0x%x' % (len(data), paddr))

        return success_status

    def search_bytes16(self, start_paddr, window_size, byte_array):
        return spi_search_bytes16(start_paddr, window_size, byte_array)

    def search_bytes32(self, start_paddr, window_size, byte_array):
        return spi_search_bytes32(start_paddr, window_size, byte_array)


def recv_into_blocking(sock, rbuf, count):
    while count > 0:
        bytes_read = sock.readinto(rbuf, count)
        count -= bytes_read
