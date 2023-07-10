import argparse
import curses
import os
import traceback
import time
import requests
import socket
import struct
import base64
from tabulate import tabulate
from operator import itemgetter


class Config(object):
    def __init__(self):
        self.mac_to_hostname = {}
        self.sleep_time = 1.0
        self.global_unit = 'kB'
        self.terminal_available = False
        self.curses_screen = None
        self.sort_key = StatKeys.BYTE_PER_SECOND_KEY
        self.running = True
        self.should_reset = False
        self.should_reset_hostnames = True
        self.summary_mode = False


class HostnameKeys(object):
    IP_ADDRESS_KEY = 'IPAddress'
    MAC_ADDRESS_KEY = 'MACAddress'
    HOST_NAME_KEY = 'hostName'


class StatKeys(object):
    IP_ADDRESS_KEY = 'ipAddress'
    MAC_ADDRESS_KEY = 'macAddress'
    TOTAL_BYTES_KEY = 'totalBytes'
    CURRENT_BYTES_KEY = 'currBytes'
    BYTE_PER_SECOND_KEY = 'bytesPerSec'

    '''
    Possible keys coming from modem are:
        'ipAddress',
        'macAddress',
        'totalPkts',
        'totalBytes',
        'currPkts',
        'currBytes',
        'currIcmp',
        'currUdp',
        'currSyn',
        'currIcmpMax',
        'currUdpMax',
        'currSynMax',

     Self added keys:
        'bytesPerSec'
    '''


class FakeCurses(object):
    def addstr(self, s):
        print s

    def refresh(self):
        pass

    def clear(self):
        os.system('clear')

    @classmethod
    def endwin(self):
        pass

    def nodelay(self, b=None):
        pass

    def getch(self, prompt=None):
        # return raw_input(prompt)
        return ''

    def getkey(self, prompt=None):
        # return raw_input(prompt)
        return ''

    def getstr(self, promp=None):
        return ''


def ip_to_decimal(ip):
    return struct.unpack('!L', socket.inet_aton(ip))[0]


def decimal_to_ip(n):
    return socket.inet_ntoa(struct.pack('!L', n))


def _ask_modem_something(modem_address, modem_password, data, api_path):
    if not modem_address.startswith('http'):
        modem_address = 'http://' + modem_address.strip('/')

    api_path = api_path.lstrip('/')

    cookies = {
        'Authorization': 'Basic {}'.format(base64.b64encode(modem_password))
    }

    headers = {
        'Referer': '{}/'.format(modem_address)
    }

    r = requests.post('{}/{}'.format(modem_address, api_path), headers=headers, cookies=cookies, data=data)

    return r.content


def get_modem_mac_names(modem_address, modem_password):
    data = '[LAN_HOST_ENTRY#0,0,0,0,0,0#0,0,0,0,0,0]0,0\r\n'

    result = _ask_modem_something(modem_address, modem_password, data, api_path='cgi?5')

    return result


def get_modem_stats(modem_address, modem_password):
    data = '[STAT_CFG#0,0,0,0,0,0#0,0,0,0,0,0]0,0\r\n[STAT_ENTRY#0,0,0,0,0,0#0,0,0,0,0,0]1,0\r\n'

    result = _ask_modem_something(modem_address, modem_password, data, api_path='cgi?1&5')

    return result


def reset_modem_stats(modem_address, modem_password):
    data = '[STAT_CFG#0,0,0,0,0,0#0,0,0,0,0,0]0,1\r\naction=1\r\n'

    result = _ask_modem_something(modem_address, modem_password, data, api_path='cgi?2')

    return result


def create_mac_to_hostname(modem_mac_names_str):
    break_split = modem_mac_names_str.split('\n')
    current_mac = ''
    split_dict = {}
    for arg in break_split:
        try:
            key, value = arg.split('=')
        except:
            continue

        if key == HostnameKeys.MAC_ADDRESS_KEY:
            mac_addr = value
            if mac_addr != current_mac:
                current_mac = mac_addr

        if current_mac:
            if current_mac not in split_dict:
                split_dict[current_mac] = {}

            if key == HostnameKeys.HOST_NAME_KEY:
                split_dict[current_mac] = value

    return split_dict


def split_modem_stats(modem_stats):
    break_split = modem_stats.split('\n')
    current_ip = ''
    split_dict = {}
    for arg in break_split:
        try:
            key, value = arg.split('=')
        except:
            continue

        if key == StatKeys.IP_ADDRESS_KEY:
            ip_addr = decimal_to_ip(int(value))
            if ip_addr != current_ip:
                current_ip = ip_addr
                value = ip_addr

        if current_ip:
            if current_ip not in split_dict:
                split_dict[current_ip] = {StatKeys.BYTE_PER_SECOND_KEY: 0}

            if key not in [StatKeys.IP_ADDRESS_KEY, StatKeys.MAC_ADDRESS_KEY]:
                value = int(value)

            split_dict[current_ip][key] = value

    return split_dict


def display_current_stats(current_stats, unit=None):
    curses_screen = configs.curses_screen

    curses_screen.clear()

    convert_values = {'B': 1, 'kB': float(1)/float(1024),
                      'b': 8, 'kb': float(1)/float(1024) * 8,
                      'mb': float(1)/float(1024**2) * 8, 'mB': float(1)/float(1024**2)}

    if not unit:
        unit = configs.global_unit

    if unit not in convert_values:
        unit = 'kB'

    convert_value = convert_values.get(unit)

    if configs.summary_mode is True:
        header_arr = ['IP', "Name", 'Cur({}ps)'.format(unit), 'Tot({})'.format(unit)]
    else:
        header_arr = ['IP', 'MAC', "Name", 'Current ({}ps)'.format(unit), 'Total ({})'.format(unit)]

    tab_array = []
    for machine_stat in current_stats:
        arr = [machine_stat.get(StatKeys.IP_ADDRESS_KEY), machine_stat.get(StatKeys.MAC_ADDRESS_KEY),
                          configs.mac_to_hostname.get(machine_stat.get(StatKeys.MAC_ADDRESS_KEY), '-'),
                          round(machine_stat.get(StatKeys.BYTE_PER_SECOND_KEY) * convert_value, 2),
                          int(machine_stat.get(StatKeys.TOTAL_BYTES_KEY) * convert_value)]
        if configs.summary_mode is True:
            del arr[1]
            name_field = arr[1]
            if len(name_field) > 9:
                arr[1] = name_field[0:9]

        tab_array.append(arr)

    curses_screen.addstr(tabulate(tab_array, headers=header_arr, tablefmt="psql"))
    if configs.summary_mode is True:
        help_str = '\n\n(m)Toggle MAC: '
    else:
        help_str = '\n\n(q)Quit (t,c,i)Sort Total,Current,IP (r)Reset Totals (h)Reset Hostnames (m)Toggle MAC (u)Change Unit: '

    curses_screen.addstr(help_str)
    curses_screen.refresh()

    curses_screen.nodelay(True)
    try:
        char = curses_screen.getkey()
        if char in ['c', 'C']:
            configs.sort_key = StatKeys.BYTE_PER_SECOND_KEY
        elif char in ['t', 'T']:
            configs.sort_key = StatKeys.TOTAL_BYTES_KEY
        elif char in ['m', 'M']:
            configs.summary_mode = not configs.summary_mode
        elif char in ['u', 'U']:
            curses_screen.nodelay(False)
            curses_screen.addstr('\n\nEnter unit: ')
            curses_screen.refresh()
            string = curses_screen.getstr()
            configs.global_unit = string
        elif char in ['q', 'Q']:
            configs.running = False
        elif char in ['r', 'R']:
            curses_screen.nodelay(False)
            curses_screen.addstr('\n\nAre you sure you want to reset data? (y/n): ')
            curses_screen.refresh()
            inner_char = curses_screen.getkey()
            if inner_char in ['y', 'Y']:
                configs.should_reset = True
        elif char in ['h', 'H']:
            configs.should_reset_hostnames = True
        elif char in ['i', 'I']:
            configs.sort_key = StatKeys.IP_ADDRESS_KEY
    except:
        pass


def run_indefinitely(modem_address, modem_password):
    last_run_dict = {}
    while configs.running:
        if configs.should_reset is True:
            reset_modem_stats(modem_address, modem_password)
            configs.should_reset = False
            last_run_dict = {}

        if configs.should_reset_hostnames is True:
            configs.mac_to_hostname = create_mac_to_hostname(get_modem_mac_names(ip_addr, modem_password))
            configs.should_reset_hostnames = False

        modem_stats = get_modem_stats(modem_address, modem_password)
        per_ip_modem_stats = split_modem_stats(modem_stats)

        for ip, ip_stats in per_ip_modem_stats.items():
            if ip in last_run_dict:
                last_total_bytes = last_run_dict[ip].get(StatKeys.TOTAL_BYTES_KEY)
                current_total_bytes = ip_stats.get(StatKeys.TOTAL_BYTES_KEY)
                per_second = float(current_total_bytes - last_total_bytes) / float(configs.sleep_time)
                ip_stats[StatKeys.BYTE_PER_SECOND_KEY] = round(per_second, 2)

        sorted_list = sorted(per_ip_modem_stats.values(), key=itemgetter(configs.sort_key), reverse=True)
        display_current_stats(sorted_list)
        last_run_dict = dict(per_ip_modem_stats)
        time.sleep(configs.sleep_time)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-a', action='store', dest='ip_addr', help='Modem address (Optional, defaults to: 192.168.1.1)', default='192.168.1.1',
                        required=False)
    parser.add_argument('-u', action='store', dest='unit', help='Unit: b, B, kb, kB, mb, mB (Optional, defaults to: kB)', default='kB',
                        required=False)
    parser.add_argument('-s', action='store', dest='sleep_time', help='Sleep time between each request in float seconds (Optional, defaults to: 1, minimum: 0.5)',
                        default=1, required=False, type=float)
    parser.add_argument('-p', action='store', dest='password', help='Modem password (Mandatory)', default=False,
                        required=True)
    parser.add_argument('--reset', action='store_true', dest='reset', help='Reset usage data (equivalent to using the reset button in statistics menu of web interface)', default=False,
                        required=False)
    parser.add_argument('--summary', action='store_true', dest='summary', help='Open Sherry in summary mode (No MAC column)', default=False, required=False)
    parser.add_argument('--new', action='store_true', dest='summary', help='Open Sherry in summary mode (No MAC column)', default=False, required=False)

    results = parser.parse_args()

    ip_addr = results.ip_addr

    global configs
    configs = Config()

    configs.sleep_time = results.sleep_time
    if configs.sleep_time < 0.5:
        raise Exception('sleep_time can not be less than 0.5')

    configs.global_unit = results.unit
    if results.summary is True:
        configs.summary_mode = True

    if os.environ.get("TERM"):
        stdscr = curses.initscr()
    else:
        print '\n##################\nRunning in no Terminal mode...\n###################\n'
        time.sleep(1)
        stdscr = FakeCurses()
        curses = FakeCurses

    configs.curses_screen = stdscr
    configs.should_reset = results.reset

    try:
        run_indefinitely(ip_addr, results.password)
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        traceback.print_exc()
    finally:
        curses.endwin()
