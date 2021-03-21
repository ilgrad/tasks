#!/usr/bin/env python
'''
Car distance utility
author: ilya.gradina@gmail.com
'''
import argparse

import numpy as np
import pandas as pd
import plotly.express as px


def haversine_np(lon1, lat1, lon2, lat2, r_geoc):
    '''
    https://en.wikipedia.org/wiki/Haversine_formula
    :return: distance in meter
    '''
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    temp = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) *\
        np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    return 2 * r_geoc * np.arcsin(np.sqrt(temp))


def get_distance(url: str, verbose: bool = False,
                 type_gs: str = 'wgs84',
                 plot_map: bool = False) -> None:
    '''
    Get distance by url
    :param url: url to json or path json
    :param verbose: True or False
    :param type_gs: wgs84 or glonass
    :param plot_map: True or False
    :return: None
    '''
    try:
        df_geo = pd.read_json(url, lines=True)
    except ValueError:
        print('url not correct, need url to json')
        return None
    df_geo = df_geo.sort_values(by='ts')
    df_geo = df_geo.reset_index(drop=True)
    df_geo['ts'] = pd.to_datetime(df_geo['ts'])
    df_geo['lat'] =\
        df_geo['geo'].apply(lambda x: x['lat'] if isinstance(x, dict) else None)
    df_geo['lon'] =\
        df_geo['geo'].apply(lambda x: x['lon'] if isinstance(x, dict) else None)
    df_geo = df_geo.drop(columns=['geo'])
    df_geo['control_switch_on'] = df_geo['control_switch_on'].fillna(method='ffill')
    ind_start = df_geo[df_geo['control_switch_on'].notna()].index[0]
    df_geo = df_geo[ind_start:]
    df_geo.loc[df_geo['control_switch_on'] == 0, 'control_switch_on'] = 'manual_mode'
    df_geo.loc[df_geo['control_switch_on'] == 1, 'control_switch_on'] = 'auto_mode'
    df_geo.loc[(df_geo['lat'] == 0) & (df_geo['lon'] == 0), 'control_switch_on'] = 'no_signal'
    df_geo.loc[(df_geo['lat'] == 0) & (df_geo['lon'] == 0), ['lat', 'lon']] = None
    df_geo['lat'] = df_geo['lat'].fillna(method='ffill')
    df_geo['lon'] = df_geo['lon'].fillna(method='ffill')
    df_geo = df_geo.reset_index(drop=True)
    semi_major, semi_minor = None, None
    if type_gs == 'wgs84':
        semi_major, semi_minor = 6378137, 6356752.3142
    elif type_gs == 'glonass':
        semi_major, semi_minor = 6378136.5, 6356751.757955

    lat_mean = df_geo.lat.mean()
    # https://en.wikipedia.org/wiki/Earth_radius#Geocentric_radius
    r_geoc = np.sqrt(
        (np.power(semi_major * semi_major * np.cos(lat_mean), 2) +
         np.power(semi_minor * semi_minor * np.sin(lat_mean), 2)) /
        (np.power(semi_major * np.cos(lat_mean), 2) +
         np.power(semi_minor * np.sin(lat_mean), 2)))
    if verbose:
        print(f'usage type_gs = {type_gs}, semi_major = {semi_major}, semi_minor = {semi_minor}')
        print(f'r_geoc = {r_geoc}')

    distance = {'unit': 'metre'}
    for dist_type in ['manual_mode', 'auto_mode']:
        df_geo_temp = df_geo[df_geo['control_switch_on'] == dist_type]
        distance[dist_type] = haversine_np(
            df_geo_temp['lon'].shift(), df_geo_temp['lat'].shift(),
            df_geo_temp.loc[1:, 'lon'], df_geo_temp.loc[1:, 'lat'],
            r_geoc).dropna().sum()
    print(distance)
    if plot_map:
        center_lat = np.mean([df_geo['lat'].min(), df_geo['lat'].max()])
        fig_map = \
            px.line_mapbox(
                df_geo, lat="lat", lon="lon", color="control_switch_on",
                zoom=60, height=800).update_traces(mode='markers')
        fig_map.update_layout(
            mapbox_style="stamen-terrain", mapbox_zoom=15,
            mapbox_center_lat=center_lat,
            margin={"r": 20, "t": 100, "l": 20, "b": 20},
            title='Yandex Drive')
        fig_map.show(config={'displaylogo': False})


def main():
    '''
    Car distance utility
    :return:
    '''
    parser = argparse.ArgumentParser(description='Car distance utility')
    parser.add_argument('url', type=str,
                        help='url or path json file contain gps coordinate')
    parser.add_argument('-v', '--verbose',
                        action="store_true", help='increase output verbosity')
    parser.add_argument('-type_gs',
                        default='wgs84',
                        type=str, help='type glonass or wgs84')
    parser.add_argument('-plot_map',
                        default='False', type=str, help='plot map, True or False')
    args = parser.parse_args()
    #if args.plot_map:
    args.plot_map = True if args.plot_map == 'True' else False
    get_distance(url=args.url,
                 verbose=args.verbose,
                 type_gs=args.type_gs, plot_map=args.plot_map)


if __name__ == '__main__':
    main()
