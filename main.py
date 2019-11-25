import picodma_radio.config
import picodma_radio.server
import picodma_radio.wlan

import logging

logger = logging.getLogger('picodma_radio')


def print_banner():
    logger.info('picodma_radio: blackhat 2019 release')

def init():
    logger.info("initializing system.")

    logging.basicConfig(level=picodma_radio.config.logging_level)

    if picodma_radio.config.ftp_and_telnet_enable:
        username = picodma_radio.config.ftp_username
        password = picodma_radio.config.ftp_password
        timeout = picodma_radio.config.ftp_timeout

        picodma_radio.server.ftp_and_telnet_enable(username, password, timeout)
    else:
        picodma_radio.server.ftp_and_telnet_disable()

    # spawn ap or connect to known wireless networks
    # be careful changing this code - if you fail to configure things
    # correctly, you may lose access to the device.
#    if picodma_radio.config.wlan_ap_enable:
#        config_ap()
    if picodma_radio.config.wlan_station_enable:
        ssid = picodma_radio.config.wlan_station_ssid
        password = picodma_radio.config.wlan_station_password
        picodma_radio.wlan.connect_wpa2(ssid, password)
#   else:
#       picodma_radio.wlan.disable()

    # start dma server
    if picodma_radio.config.dma_server_enable:
        ip = picodma_radio.config.dma_server_ip
        port = picodma_radio.config.dma_server_port

        picodma_radio.server.spawn_dma_server(ip, port)

    logger.info("done initializing system.")


print_banner()
init()
