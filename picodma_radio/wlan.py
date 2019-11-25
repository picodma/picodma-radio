import machine
import logging

from network import WLAN

logger = logging.getLogger('picodma_radio.wlan')

def connect_known_wlan(known_wlans):
    wlan = WLAN(mode=WLAN.STA)

    available_wlans = wlan.scan()
    seen_ssids = frozenset([w.ssid for w in available_wlans])
    known_ssids = frozenset([ssid for ssid in known_wlans])
    ssids_to_use = list(seen_ssids & known_ssids)

    # connect to first known wlan seen
    for ssid in ssids_to_use:
        auth_tuple = None
        net_properties = known_wlans[ssid]
        net_config = net_properties['net_config']
        auth = net_properties['auth']

        if auth == WLAN.WPA2:
            password = net_properties['password']
            auth_tuple = (WLAN.WPA2, password)

        if net_config and _connect(wlan, ssid, net_config, auth_tuple):
            logger.info("connected to %s" % str(wlan.ifconfig()))
            return True
        elif _connect(wlan, ssid, auth_tuple):
            logger.info("connected to %s" % str(wlan.ifconfig()))
            return True


    logger.error("saw %s, failed to connect to any." % str(seen_ssids))
    return False


def disable():
    wlan = WLAN()

    logger.info("disabling wlan.")
    wlan.deinit()


def connect_wpa2(ssid, password):
    wlan = WLAN(mode=WLAN.STA)

    is_connected = _connect(wlan, ssid, 'dhcp', (WLAN.WPA2, password))
    if is_connected:
        logger.info("connected to %s" % str(wlan.ifconfig()))

    return is_connected


def config_ap(ssid, channel, auth_tuple, antenna, net_config):
    AP_INTERFACE_ID = 1

    wlan = WLAN.init(mode=WLAN.AP, ssid=ssid, auth=auth_tuple, channel=channel, antenna=antenna)
    wlan.ifconfig(id=AP_INTERFACE_ID, config=net_config)


def _connect(wlan, ssid, net_config, auth_tuple=None, timeout=10000):
    wlan.ifconfig(config=net_config)
    wlan.connect(ssid, auth=auth_tuple, timeout=timeout)

    # save power while waiting
    while not wlan.isconnected():
        machine.idle()

    # True unless we timed out
    return wlan.isconnected()
