### Info
```
(pyenv39) [ilgrad@x230 yandex_self_driving_car]$ python3.9 task_drive.py -h
usage: task_drive.py [-h] [-v] [-type_gs TYPE_GS] [-plot_map PLOT_MAP] url

Car distance utility

positional arguments:
  url                 url or path json file contain gps coordinate

optional arguments:
  -h, --help          show this help message and exit
  -v, --verbose       increase output verbosity
  -type_gs TYPE_GS    type glonass or wgs84
  -plot_map PLOT_MAP  plot map, True or False
```

#### run example with map
```
(pyenv39) [ilgrad@x230 yandex_self_driving_car]$ python3.9 task_drive.py data.json -type_gs glonass -plot_map True -v
usage type_gs = glonass, semi_major = 6378136.5, semi_minor = 6356751.757955
r_geoc = 6356763.242034094
{'unit': 'metre', 'manual_mode': 1223.021833941339, 'auto_mode': 2687.8767550746534}
```
