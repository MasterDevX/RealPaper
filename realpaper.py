import time
import struct

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker

from math import *
from os import getcwd
from itertools import count
from datetime import datetime, timedelta
from subprocess import run, check_output
from multiprocessing import Process, freeze_support

def init():
    cfg_name = './config.dat'
    actions = {1: run_sync, 2: make_cfg, 3: show_cfg}
    while True:
        try:
            clear()
            print('RealPaper v1.0.1')
            print('----------------')
            print('1 - Run RealPaper')
            print('2 - Create new configuration')
            print('3 - Show current configuration')
            print('0 - Exit')
            action = int(input(': '))
            if action < 0 or action > 3:
                raise ValueError
            if action == 0:
                break
            actions[action](cfg_name)
        except:
            pass

def make_cfg(cfg_name):
    while True:
        try:
            clear()
            print('Type in latitude (in degrees)')
            print('Floating point value in range: [-90; 90]')
            lat = float(input(': '))
            if lat < -90 or lat > 90:
                raise ValueError
            break
        except:
            pass
    while True:
        try:
            clear()
            print('Type in longitude (in degrees)')
            print('Floating point value in range: [-180; 180]')
            lon = float(input(': '))
            if lon < -180 or lon > 180:
                raise ValueError
            break
        except:
            pass
    while True:
        try:
            clear()
            print('Type in sync interval (in seconds)')
            print('Integer value in range: [1; ∞)')
            s_itv = int(input(': '))
            if s_itv < 1:
                raise ValueError
            break
        except:
            pass
    while True:
        try:
            clear()
            print('Enable graphs? (0 - No, 1 - Yes)')
            print('Boolean value in range: [0; 1]')
            graphs = int(input(': '))
            if graphs != 0 and graphs != 1:
                raise ValueError
            graphs = bool(graphs)
            break
        except:
            pass
    if graphs:
        while True:
            try:
                clear()
                print('Type in graphs drawing interval (in syncs)')
                print('Integer value in range: [1; ∞)')
                g_itv = int(input(': '))
                if g_itv < 1:
                    raise ValueError
                break
            except:
                pass
    else:
        g_itv = 0
    with open(cfg_name, 'wb') as cfg:
        cfg.write(struct.pack('2di?i', lat, lon, s_itv, graphs, g_itv))
    clear()
    print('Configuration file written!')
    print()
    input('Press Enter to go back...')

def show_cfg(cfg_name):
    try:
        lat, lon, s_itv, graphs, g_itv = read_cfg(cfg_name)
        clear()
        print('Current configuration:')
        print()
        print(f' - Latitude:           {lat} degrees')
        print(f' - Longitude:          {lon} degrees')
        print(f' - Sync interval:      {s_itv} seconds')
        if graphs:
            print(f' - Graphs:             Enabled')
            print(f' - Graphs interval:    {g_itv} syncs')
        else:
            print(f' - Graphs:             Disabled')
            print(f' - Graphs interval:    -')
    except:
        clear()
        print('RealPaper is not configured yet!')
    finally:
        print()
        input('Press Enter to go back...')

def read_cfg(cfg_name):
    with open(cfg_name, 'rb') as cfg:
        return struct.unpack('2di?i', cfg.read())

def run_sync(cfg_name):
    try:
        lat, lon, s_itv, graphs, g_itv = read_cfg(cfg_name)
    except:
        clear()
        print('RealPaper is not configured yet!')
        print()
        input('Press Enter to go back...')
        return
    wall_get = 'gsettings get org.cinnamon.desktop.background picture-uri'
    wall_set = 'gsettings set org.cinnamon.desktop.background picture-uri'
    wall_old = check_output(wall_get, shell=True).decode()[1:-2]
    wall_now = None
    cwd = getcwd()
    for i in count(0):
        try:
            time_init = time.time()
            date_obj = datetime.now()
            data = make_data(date_obj, lat, lon)
            clear()
            print('RealPaper is running')
            print('Press Ctrl + C to stop')
            print()
            print(f'Sync №{i}')
            print()
            print(f'Syncing every {s_itv} seconds')
            if graphs:
                print(f'Drawing graphs every {g_itv} syncs')
            else:
                print('Graphs are disabled')
            print()
            print(f'Date: {date_obj.strftime("%Y/%m/%d")}')
            print(f'Time: {date_obj.strftime("%H:%M:%S")}')
            print()
            print(f'Latitude:  {lat}')
            print(f'Longitude: {lon}')
            print()
            print('Altitude:')
            print(f' - Real       = {round(data[1][0], 3)}')
            print(f' - Normalized = {round(data[2][0], 3)}')
            print(f' - Sawtooth   = {round(data[3][0], 3)}')
            print()
            saw_approx = round(data[3][0])
            if saw_approx == 360:
                saw_approx = 0
            print(f'Sawtooth: {round(data[3][0], 3)} -> approx. = {saw_approx}')
            if saw_approx != wall_now:
                if wall_now != None:
                    print(f'Image:    {wall_now}.png -> {saw_approx}.png')
                else:
                    print(f'Image:    None -> {saw_approx}.png')
                run(f'{wall_set} file://{cwd}/images/{saw_approx}.png', shell=True)
                wall_now = saw_approx
            else:
                print(f'Image:    {wall_now}.png (no changes)')
            if graphs:
                if (i % g_itv) == 0:
                    graph_name = f'{date_obj.strftime("%Y-%m-%d-%H-%M-%S")}.png'
                    print(f'Graph:    {graph_name}')
                    run_as_process(draw_graph, data, graph_name)
                else:
                    print(f'Graph:    {i % g_itv}/{g_itv} syncs since last')
            else:
                print(f'Graph:    Disabled')
            print()
            time_elapsed = time.time() - time_init
            print(f'Synced in {round(time_elapsed, 3)}s')
            if time_elapsed < s_itv:
                time.sleep(s_itv - time_elapsed)
        except KeyboardInterrupt:
            run(f'{wall_set} {wall_old}', shell=True)
            break

def get_alt(date_obj, lat, lon):
    t = (date_obj.hour * 60 + date_obj.minute + date_obj.second / 60) / 1440
    tz = date_obj.astimezone().tzinfo.utcoffset(date_obj.astimezone()).seconds / 3600
    dse = (date_obj - datetime(2000, 1, 1)).days + 36526
    jd = dse + 2415018.5 + t - tz / 24
    jc = (jd - 2451545) / 36525
    gmls = (280.46646 + jc * (36000.76983 + jc * 0.0003032)) % 360
    gmas = 357.52911 + jc * (35999.05029 - 0.0001537 * jc)
    eeo = 0.016708634 - jc * (0.000042037 + 0.0000001267 * jc)
    seoc = sin(rad(gmas)) * (1.914602 - jc * (0.004817 + 0.000014 * jc)) \
        + sin(rad(2 * gmas)) * (0.019993 - 0.000101 * jc) \
        + sin(rad(3 * gmas)) * 0.000289
    stl = gmls + seoc
    sal = stl - 0.00569 - 0.00478 * sin(rad(125.04 - 1934.136 * jc))
    moe = 23 + (26 + (21.448 - jc * (46.815 + jc * (0.00059 - jc * 0.001813))) / 60) / 60
    oc = moe + 0.00256 * cos(rad(125.04 - 1934.136 * jc))
    sd = deg(asin(sin(rad(oc)) * sin(rad(sal))))
    vy = tan(rad(oc / 2)) ** 2
    eot = 4 * deg(vy * sin(2 * rad(gmls)) \
        - 2 * eeo * sin(rad(gmas)) \
        + 4 * eeo * vy * sin(rad(gmas)) * cos(2 * rad(gmls)) \
        - 0.5 * vy ** 2 * sin(4 * rad(gmls)) \
        - 1.25 * eeo ** 2 * sin(2 * rad(gmas)))
    tst = (t * 1440 + eot + 4 * lon - 60 * tz) % 1440
    if tst / 4 < 0:
        ha = tst / 4 + 180
    else:
        ha = tst / 4 - 180
    sza = deg(acos(sin(rad(lat)) * sin(rad(sd)) + cos(rad(lat)) * cos(rad(sd)) * cos(rad(ha))))
    alt = 90 - sza
    if alt > 85:
        ar = 0
    else:
        if alt > 5:
            ar = 58.1 / tan(rad(alt)) \
            - 0.07 / tan(rad(alt)) ** 3 \
            + 0.000086 / tan(rad(alt)) ** 5
        else:
            if alt > -0.575:
                ar = 1735 + alt * (-518.2 + alt * (103.4 + alt * (-12.79 + alt * 0.711)))
            else:
                ar = -20.772 / tan(rad(alt))
    alt += ar / 3600
    return alt

def make_data(date_obj, lat, lon):
    dates = np.array([date_obj + timedelta(minutes=i) for i in range(1441)])
    data_real = np.array([get_alt(i, lat, lon) for i in dates])
    data_normalized = np.copy(data_real)
    data_normalized[data_normalized > 0] *= 90 / data_normalized.max()
    data_normalized[data_normalized < 0] *= -90 / data_normalized.min()
    data_saw = np.concatenate(([0], data_normalized))
    data_shifted = np.concatenate((data_normalized, [0]))
    data_saw[data_saw > data_shifted] *= -1
    data_saw = np.delete(data_saw, 0)
    data_saw = np.delete(data_saw, -1)
    data_saw += 180 * np.concatenate(([0], np.diff(data_saw) < -90)).cumsum()
    if data_normalized[0] > data_normalized[1]:
        data_saw += 180
    while (data_saw > 360).any():
        data_saw[data_saw > 360] -= 360
    while (data_saw < 0).any():
        data_saw[data_saw < 0] += 360
    return [dates[:-1], data_real[:-1], data_normalized[:-1], data_saw]

def draw_graph(data, name):
    plt.style.use('./realpaper.mplstyle')
    plt.xlabel(f'\nLocal Time [{data[0][0].astimezone().tzname()}]')
    plt.ylabel('Solar Altitude Angle (°)')
    plt.plot(data[0], data[1], label='Real', lw=3)
    plt.axhline(y=data[1].max(), label='Real Range', c='#8282F3', ls='--')
    plt.axhline(y=data[1].min(), c='#8282F3', ls='--')
    plt.plot(data[0], data[2], label='Normalized', lw=3)
    plt.axhline(y=90, label='Normalized Range', c='#EF4B56', ls='--')
    plt.axhline(y=-90, c='#EF4B56', ls='--')
    plt.plot(data[0], data[3], label='Sawtooth', lw=3)
    plt.axhline(y=360, label='Sawtooth Range', c='#23C766', ls='--')
    plt.axhline(y=0, c='#23C766', ls='--')
    plt.gca().xaxis.set_major_locator(mdates.HourLocator())
    plt.gca().yaxis.set_major_locator(mticker.MultipleLocator(45))
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y.%m.%d\n%H:%M'))
    plt.xticks(rotation=90)
    plt.grid()
    plt.legend()
    plt.tight_layout()
    plt.savefig(f'./graphs/{name}')
    plt.close()

def run_as_process(func, *args):
    p = Process(target=func, args=args)
    try:
        p.start()
        p.join()
    except:
        pass
    finally:
        p.terminate()

clear = lambda : run('clear', shell=True)

deg = lambda radians : (180 / pi) * radians
rad = lambda degrees : (pi / 180) * degrees

if __name__ == '__main__':
    freeze_support()
    init()
