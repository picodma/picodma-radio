import _thread
import logging
import network
import socket

from struct import pack, unpack_from

from .dma import spi_dma
from . import config

logger = logging.getLogger('picodma_radio.server')


def ftp_and_telnet_enable(username, password, timeout):
    server = network.Server()

    server.deinit() # disable the server
    server.init(login=(username, password), timeout=timeout)

    logger.info("ftp/telnet up, username: %s, timeout: %s." % (username, timeout))


def ftp_and_telnet_disable():
    server = network.Server()

    server.deinit() # disable the server
    logger.info("ftp/telnet disabled.")


# Code below for pcileech integration referenced https://github.com/Synacktiv-contrib/pcileech_hpilo4_service
# Big thank you to the folks at Synactiv for sharing this code and for the excellent research!

STATUS = 0
MEM_READ = 1
MEM_WRITE = 2

def recv_bytes(sock, count, buf):
    logger.info("receiving %d bytes." % count)

    while count > 0:
        next_bytes = sock.recv(count)
        count -= len(next_bytes)
        result += next_bytes

    logger.info("received %d bytes." % count)

    return result


def read_command(sock, buffered=True):
    if buffered:
        command = recv_bytes(sock, 24)
    else:
        command = sock.recv(24)
        if not command:
            return None

    cmd_id, paddr, count = unpack_from("<3Q", command)
    logger.info("got cmd: %x, paddr: %x, count: %x" % (cmd_id, paddr, count))

    return (cmd_id, paddr, count)


def send_command(sock, cmd_id, paddr, count, data=''):
    buf = pack("<3Q", cmd_id, paddr, count)
    buf += data

    sock.send(buf)
    logger.debug("sent cmd: %x, paddr: %x, count: %x, len(data): %d" % (cmd_id, paddr, count, len(data)))


MAX_MEMORY = 8 * 1024 * 1024 * 1024

def read_memory(sock, dma, paddr, count):
    logger.debug("asked read of %08x bytes at %016x" % (count, paddr))

    if paddr >= MAX_MEMORY:
        send_command(sock, MEM_READ, paddr, 0)
        return True

    # ack read command, stream read data
    send_command(sock, MEM_READ, paddr, count)
    read_result = dma.read_pa_stream(sock, paddr, count, pad_zeros=True)

    if read_result:
        logger.info("read %d bytes at paddr: %x" % (count, paddr))
        return True
    else:
        logger.error("streaming read %d bytes at paddr: %x failed" % (count, paddr))
        return False


def write_memory(sock, dma, paddr, count):
    logger.info("write %08x bytes to %016x" % (count, paddr))

    write_result = dma.write_pa_stream(sock, paddr, count, pad_zeros=True)

    if write_result:
        logger.info("streaming wrote %d bytes to paddr: %x" % (paddr, count))
        send_command(sock, MEM_WRITE, paddr, count)
        return True
    else:
        logger.info("streaming wrote %d bytes to paddr: %x failed" % (paddr, count))
        return False


def handle_request(sock, dma, command_tuple):
    cmd_id, paddr, count = command_tuple

    if cmd_id == STATUS:
        status = 1
        send_command(sock, cmd_id, 0, 1, chr(status))
        return True

    elif cmd_id == MEM_READ:
        return read_memory(sock, dma, paddr, count)

    elif cmd_id == MEM_WRITE:
        return write_memory(sock, dma, paddr, count)


def dma_server(ip, port):
    config.dma_server_is_running = True
    dma = spi_dma()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (ip, port)
    sock.bind(server_address)
    sock.listen(1)

    logger.info("dma server thread listening on %d." % port)

    while True:
        connection, client_address = sock.accept()

        try:
            while True:
                command = read_command(connection, buffered=False)
                if not command or not handle_request(connection, dma, command):
                    break

        except Exception as e:
            logger.exception(e)

        finally:
            connection.close()


def spawn_dma_server(ip, port):
    logger.info("spawning dma server thread on %s, %d." % (ip, port))

    _thread.start_new_thread(dma_server, (ip, port))
