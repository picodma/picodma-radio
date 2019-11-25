import logging
import struct
import time

from machine import SPI
from machine import Pin

from . import config

logger = logging.getLogger('picodma_radio.spi')

# load configuration

SPI_LOW  = 0
SPI_HIGH = 1

SPI_CS   = config.SPI_CS
SPI_MOSI = config.SPI_MOSI
SPI_MISO = config.SPI_MISO
SPI_CLK  = config.SPI_CLK

baudrate = config.spi_baudrate

spi_cs = Pin(SPI_CS, mode = Pin.OUT)
spi = SPI(0, mode=SPI.MASTER, baudrate=baudrate, pins=(SPI_CLK, SPI_MOSI, SPI_MISO), polarity=0, phase=0)

spi_cs.value(SPI_LOW)

SPI_READ_REGISTER  = 0x00
SPI_WRITE_REGISTER = 0x80

BUFFER_READ   = 0x0
BUFFER_SEARCH = 0x1
BUFFER_RX_MEM = 0x2
BUFFER_TX_MEM = 0x3

# https://github.com/PicoDMA/picodma-fpga

SPI_ADDR0                    = 0
SPI_ADDR1                    = 1
SPI_PCI_WRITE_TRIGGER        = 2
SPI_SEARCH_LENGTH            = 3
SPI_VAL0                     = 4
SPI_VAL1                     = 5
SPI_BUFFER_SELECT            = 6
SPI_BUFFER_VALUE             = 7
SPI_BUFFER_OFFSET            = 8
SPI_PCI_READ_BUSY            = 9
SPI_PCI_READ_TRIGGER         = 10
SPI_PCI_READ_FAILED          = 11
SPI_PCI_READ_LENGTH          = 12
SPI_CURRENT_INDEX            = 13
SPI_PCI_SEARCH_BUSY          = 14
SPI_PCI_SEARCH_TRIGGER       = 15
SPI_PCI_SEARCH_FAILED        = 16
SPI_PCI_SEARCH_LENGTH        = 17
SPI_SEARCH_TYPE              = 18
SPI_SEARCH_VALUE             = 19

# Debug commands

SPI_PCI_REQUESTER            = 20
SPI_PCI_TX_BUFFER_COUNT      = 21
SPI_PCI_TX_WRITER_READY      = 22
SPI_PCI_TX_ERR_COUNT         = 23
SPI_PCI_TX_SENT_COUNT        = 24
SPI_PCI_TX_IS_READY          = 25
SPI_PCI_READ_TRIGGER_COUNT   = 26
SPI_PCI_SEARCH_TRIGGER_COUNT = 27

def _raw_spi(op, payload):
    spi_cs.value(SPI_HIGH)
    rbuf = bytearray(1+len(payload))
    opByte = bytes([op])
    spi.write_readinto(opByte+payload, rbuf)
    spi_cs.value(SPI_LOW)
    return rbuf[1:]

def _raw_read(op):
    value = _raw_spi(op | SPI_READ_REGISTER, bytes(4*[0x00]))
    return struct.unpack("<I", value)[0]

def _raw_read_buffer(count):
    return _raw_spi(SPI_BUFFER_VALUE | SPI_READ_REGISTER, bytes(count*[0x00]))

def _raw_write(op, value):
    packed = struct.pack("<I", value)
    _raw_spi(op | SPI_WRITE_REGISTER, packed)

def _raw_rx_buff(length):
    _raw_write(SPI_BUFFER_SELECT, 2)
    return _raw_read_buffer(length)
def _raw_tx_buff(length):
    _raw_write(SPI_BUFFER_SELECT, 3)
    return _raw_read_buffer(length)

# ---

def dma_async_read(addr):
    _raw_write(SPI_ADDR0, addr & 0xFFFFFFFF)
    _raw_write(SPI_ADDR1, addr >> 32)
    _raw_write(SPI_PCI_READ_TRIGGER, 0x1)

def dma_read_length():
    return _raw_read(SPI_PCI_READ_LENGTH) * 8
def dma_read_has_failed():
    return _raw_read(SPI_PCI_READ_FAILED)

def dma_read_buffer():
    _raw_write(SPI_BUFFER_SELECT, BUFFER_READ)
    length = dma_read_length()
    return _raw_read_buffer(length)


# # function for writing to memory

def dma_write(addr, value):
    _raw_write(SPI_ADDR0, addr & 0xFFFFFFFF)
    _raw_write(SPI_ADDR1, addr >> 32)
    _raw_write(SPI_VAL0, value & 0xFFFFFFFF)
    _raw_write(SPI_VAL1, value >> 32)
    _raw_write(SPI_PCI_WRITE_TRIGGER, 0x1)

# # probe for readable memory regions
# # TODO: need to add this back to new FPGA code

# def dma_probe(low, high):
#     if (high > (low + 4096 * 65)):
#         logger.error('Only support 64 page probe')
#     else:
#         low = struct.pack("<Q", low)
#         high = struct.pack("<Q", high)
#         _raw_write(SPI_DMA_PROBE, low + high)

# def dma_probe_result():
#     return _raw_read(SPI_DMA_PROBE_RESULT, 8)[2:]


# # FPGA search functions

def dma_search(addr, length, value, type):
    # SPI search length is in 32bit chunks
    length = length >> 2
    _raw_write(SPI_ADDR0, addr & 0xFFFFFFFF)
    _raw_write(SPI_ADDR1, addr >> 32)
    _raw_write(SPI_SEARCH_VALUE, value)
    _raw_write(SPI_SEARCH_TYPE, type)
    _raw_write(SPI_SEARCH_LENGTH, length)
    _raw_write(SPI_PCI_SEARCH_TRIGGER, 0x1)

def dma_search16(addr, length, value):
    dma_search(addr, length, value, 1)

def dma_search32(addr, length, value):
    dma_search(addr, length, value, 2)

def dma_search_length():
    return _raw_read(SPI_PCI_SEARCH_LENGTH)
def dma_search_has_failed():
    return _raw_read(SPI_PCI_SEARCH_FAILED)
def dma_search_busy():
    return _raw_read(SPI_PCI_SEARCH_BUSY)

def dma_search_results(base_addr):
    _raw_write(SPI_BUFFER_SELECT, BUFFER_SEARCH)
    length = dma_search_length()
    buff = _raw_read_buffer(length * 8)
    for i in range(0, len(buff), 8):
        yield (struct.unpack("<Q", buff[i: i + 8]) + base_addr)

# # SPI health test functions

def test_spi():
    logger.info("Running SPI health test...")

    buff = _raw_spi(SPI_CURRENT_INDEX, bytes(40*[0x00]))
    if buff != bytes(range (0,40)):
        logger.debug('Failed SPI byte index test!')

    _raw_write(SPI_ADDR0, 0x12345678)
    _raw_write(SPI_ADDR1, 0x9abcdef0)
    if _raw_read(SPI_ADDR0) != 0x12345678:
        logger.debug('Failed ADDR0 readback!')
    if _raw_read(SPI_ADDR1) != 0x9abcdef0:
        logger.debug('Failed ADDR1 readback!')
    _raw_write(SPI_ADDR0, 0)
    _raw_write(SPI_ADDR1, 0)
    if _raw_read(SPI_ADDR0) != 0:
        logger.debug('Failed ADDR0 readback!')
    if _raw_read(SPI_ADDR1) != 0:
        logger.debug('Failed ADDR1 readback!')

    logger.info("done.")

def test_pcie():
  for i in range (0,10):
    print("read %d" % i)
    dma_async_read(0)
    length = dma_read_length()
    failed = dma_read_has_failed()
    if length < 512 or failed == 1:
        print("read %d failed: len %d status %d" % (i, length, status))
    # device specific
    # buff = dma_read_buffer()[:4]
    # if buff != b'\xf3\xee\x00\xf0':
    #     sbuff = print("".join("\\x%02x" % x for x in buff))
    #     print("read %d data looks wrong: %s" % (i, sbuff))
    time.sleep(1)

