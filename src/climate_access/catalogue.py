"""Read the public source catalogue shipped inside the installed package."""
from importlib.resources import files
import json

ROUTES = {'earth_engine': ['era5-gee'], 'era5_hourly': ['era5-gee'],
          'nasa_power': ['nasa-power'], 'open_meteo': ['open-meteo']}


def load_catalog():
    return json.loads(files('climate_access').joinpath('resources/sources.json').read_text(encoding='utf-8'))


def search_sources(query='', tier=None):
    if not isinstance(query, str) or (tier is not None and not isinstance(tier, str)):
        raise ValueError('query and tier must be strings')
    catalog = load_catalog()
    if tier is not None and tier not in catalog['access_tier_legend']:
        raise ValueError('Unknown account tier')
    words = query.casefold().split()
    result = []
    for source in catalog['sources']:
        if tier is not None and source['public_access']['access_tier'] != tier:
            continue
        text = json.dumps(source, ensure_ascii=False).casefold()
        if all(word in text for word in words):
            result.append(dict(source, executable_routes=ROUTES.get(source['id'], [])))
    return result
