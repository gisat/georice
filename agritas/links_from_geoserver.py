import requests
import json
import re
import os


def get_list(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f'Connection failed. Status>: {response.status_code}')


def from_json(in_json):
    """return list of names to parse from json format"""
    return [name['name'] for name in in_json['layers']['layer']]


def parse_name(string, ptr):
    p = re.compile(ptr)
    return [par for pars in p.findall(string) for par in pars]


def get_pars(in_json, patern):
    names = from_json(in_json)
    return [parse_name(name, patern)+[name] for name in names]


def rearange_pars(pars_list):
    return [['Agrossyn', 'biofyzika', pars[2], pars[3], pars[1], pars[4]] for pars in pars_list]


class Object:
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)


def crt_attr(obj, pars):
    while len(pars) > 0:
        par = pars.pop(0)
        if hasattr(obj, par):
            crt_attr(getattr(obj, par), pars)
        else:
            if len(pars) > 1:
                setattr(obj, par, Object())
                crt_attr(getattr(obj, par), pars)
            else:
                setattr(obj, par, pars.pop())


patern = '[a-z]+[:]([A-Z]+)[_](\d+)[_](\d{4})\d+[_]([a-z]+[_a-z]*)'
dumps="C:\Michal\gisat\\agritas\layers.json"


with open(dumps, 'r') as f:
    layers = json.load(f)

lpars = get_pars(layers, patern)
rlpars = rearange_pars(lpars)
m=Object()
for pars in rlpars:
    crt_attr(m,pars)

with open('C:\Michal\gisat\\agritas\\agritas.json', 'w') as f:
    f.write(m.toJSON())


