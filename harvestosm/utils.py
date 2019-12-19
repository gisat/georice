import random, string
import geojson
import os

def random_name():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(5))


def get_area_tags():
    with open('../recourses/area_tags.json', 'r') as f:
        return geojson.load(f)

