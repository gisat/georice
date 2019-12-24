import random, string
import geojson
from pathlib import Path

def random_name():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(5))


def get_area_tags():
    base_path = Path(__file__).parent
    file_path = (base_path / "../utils/area_tags.json").resolve()
    with open(file_path, 'r') as f:
        return geojson.load(f)

