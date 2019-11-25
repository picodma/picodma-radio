import machine
import uos

from . import config

def print_system_info():
    os_info = uos.uname()

    print("os info:")
    print("  node: %s" % os_info.nodename)
    print("  release: %s, version: %s" % (os_info.release, os_info.version))
    print("  cpu freq: %d MHz" % int(machine.freq() / (1000**2)))
    print("")

    # print stack and heap info
    machine.info()

def print_spi_configuration():
    # hardcoded - this is by convention / spec on picodma side
    fpga_SPI_CS   = 1
    fpga_SPI_MOSI = 2
    fpga_SPI_MISO = 4
    fpga_SPI_CLK  = 5
    fpga_POWER    = 3
    fpga_GND      = 6

    print("spi running at %d baud, config:" % config.spi_baudrate)
    print("  pycom -> picoEVB")
    print('    %s -> %s (SPI_CS)' % (config.SPI_CS, fpga_SPI_CS))
    print('    %s -> %s (SPI_MOSI)' % (config.SPI_MOSI, fpga_SPI_MOSI))
    print('    %s -> %s (SPI_MISO)' % (config.SPI_MISO, fpga_SPI_MISO))
    print('    %s -> %s (SPI_CLK)' % (config.SPI_CLK, fpga_SPI_CLK))
    print('    %s -> %s (POWER)' % (config.SPI_POWER, fpga_POWER))
    print('    %s -> %s (GND)' % (config.SPI_GND, fpga_GND))

def print_pcileech_dma_server_status():
    print("dma server thread (pcileech rawtcp:// compatible):")
    print("  listens at: %s:%s" % (config.dma_server_ip, config.dma_server_port))
    print("  enabled: %s" % config.dma_server_enable)
    print("  is_running: %s" % config.dma_server_is_running)
