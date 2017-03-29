import argparse
import curses
import traceback
import time
import requests
import socket
import struct
import base64
from tabulate import tabulate
from operator import itemgetter


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

    if 'Unknown' in result:
        return get_modem_mac_names(modem_address, modem_password)
    else:
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

        if key == 'MACAddress':
            mac_addr = value
            if mac_addr != current_mac:
                current_mac = mac_addr

        if current_mac:
            if current_mac not in split_dict:
                split_dict[current_mac] = {}

            if key == 'hostName':
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

        if key == 'ipAddress':
            ip_addr = decimal_to_ip(int(value))
            if ip_addr != current_ip:
                current_ip = ip_addr
                value = ip_addr

        if current_ip:
            if current_ip not in split_dict:
                split_dict[current_ip] = {'bytesPerSec': 0}

            if key not in ['ipAddress', 'macAddress']:
                value = int(value)

            split_dict[current_ip][key] = value

    return split_dict


class MachineUsage(object):
    def __init__(self, data_dict=None):
        self.keys = ['ipAddress',
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
                     'bytesPerSec']

        if data_dict:
            for k, v in data_dict.items():
                if k not in ['ipAddress', 'macAddress']:
                    v = int(v)

                self.__setattr__(k, v)

    def __str__(self):
        return_str = '-------\n'
        for k in self.keys:
            return_str += '{}={}\n'.format(k, self.__getattribute__(k))
        return_str += '-------\n'

        return return_str


def display_current_stats(current_stats, unit=None):
    curses_screen.clear()

    convert_values = {'B': 1, 'kB': float(1)/float(1024),
                      'b': 8, 'kb': float(1)/float(1024) * 8,
                      'mb': float(1)/float(1024**2) * 8, 'mB': float(1)/float(1024**2)}

    if not unit or unit not in convert_values:
        unit = global_unit

    convert_value = convert_values.get(unit)

    header_arr = ['IP', 'MAC', "Name", 'Current ({}ps)'.format(unit), 'Total ({})'.format(unit)]
    tab_array = []
    for machine_stat in current_stats:
        tab_array.append([machine_stat.ipAddress, machine_stat.macAddress,
                          mac_to_hostname.get(machine_stat.macAddress, '-'),
                          round(machine_stat.bytesPerSec * convert_value, 2),
                          int(machine_stat.totalBytes * convert_value)])

    curses_screen.addstr(tabulate(tab_array, headers=header_arr, tablefmt="psql"))
    curses_screen.refresh()


def run_indefinitely(modem_address, modem_password):
    last_run_dict = {}
    while True:
        modem_stats = get_modem_stats(modem_address, modem_password)
        per_ip_modem_stats = split_modem_stats(modem_stats)

        for ip, ip_stats in per_ip_modem_stats.items():
            if ip in last_run_dict:
                last_total_bytes = last_run_dict[ip].get('totalBytes')
                current_total_bytes = ip_stats.get('totalBytes')
                per_second = float(current_total_bytes - last_total_bytes) / float(sleep_time)
                ip_stats['bytesPerSec'] = round(per_second, 2)

        sorted_list = sorted(per_ip_modem_stats.values(), key=itemgetter('bytesPerSec'), reverse=True)
        sorted_list = [MachineUsage(x) for x in sorted_list]
        display_current_stats(sorted_list)
        last_run_dict = dict(per_ip_modem_stats)
        time.sleep(sleep_time)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-a', action='store', dest='ip_addr', help='Modem address', default='192.168.1.1',
                        required=False)
    parser.add_argument('-u', action='store', dest='unit', help='Unit: b, B, kb, kB, mb, mB', default='kB',
                        required=False)
    parser.add_argument('-s', action='store', dest='sleep_time', help='sleep time between each request (seconds)',
                        default=1, required=False, type=int)
    parser.add_argument('--reset', action='store_true', dest='reset', help='Reset usage data', default=False,
                        required=False)
    parser.add_argument('-p', action='store', dest='password', help='Modem password', default=False,
                        required=True)

    results = parser.parse_args()

    ip_addr = results.ip_addr

    global mac_to_hostname
    mac_to_hostname = create_mac_to_hostname(get_modem_mac_names(ip_addr, results.password))

    global sleep_time
    sleep_time = results.sleep_time

    global global_unit
    global_unit = results.unit

    stdscr = curses.initscr()

    global curses_screen
    curses_screen = stdscr

    if results.reset is True:
        print 'Resetting usage data...'
        time.sleep(1)
        reset_modem_stats(ip_addr, results.password)

    try:
        run_indefinitely(ip_addr, results.password)
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        traceback.print_exc()
    finally:
        curses.endwin()
