from logging import INFO, DEBUG
from network import WLAN

# logging level: DEBUG | INFO etc
logging_level = INFO

# ftp and telnet
ftp_and_telnet_enable = True

ftp_username = 'blackhat'
ftp_password = 'heregoesnothing'
ftp_timeout = 60

# wlan station mode configuration - dhcp
wlan_station_enable = True
wlan_station_ssid = 'theodore'
wlan_station_password = 'loves.the.krinkle'

# wlan ap mode configuration
wlan_ap_enable  = False
wlan_ap_ssid    = 'recovery'
wlan_ap_channel = 7
wlan_ap_auth    = (WLAN.WPA2, 'weak_recovery_password')
wlan_ap_antenna = WLAN.INT_ANT
wlan_ap_net_config  = ('192.168.4.1', '255.255.255.0', '0.0.0.0', '0.0.0.0')

# pcileech dma server
dma_server_enable = True
dma_server_is_running = False  # thread changes this to true when started
dma_server_ip = '0.0.0.0'
dma_server_port = 9999

# SPI configuration
SPI_CS    = 'P10'
SPI_MOSI  = 'P23'
SPI_MISO  = 'P21'
SPI_CLK   = 'P22'
SPI_POWER = 'VIN'
SPI_GND   = 'GND'

spi_baudrate = 20000000
