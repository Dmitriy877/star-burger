from locations.models import Location
import requests


def get_or_create_location_object(address):
    location, created = Location.objects.get_or_create(address=address)
    return location


def get_geocoder_location_data(apikey, address):
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(base_url, params={
        "geocode": address,
        "apikey": apikey,
        "format": "json",
    })
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection']['featureMember']
    if not found_places:
        return None
    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return lon, lat


def get_or_create_location(apikey, address):

    location = get_or_create_location_object(address)
    if location.lat and location.lon:
        return location.lat, location.lon
    try:
        location.lon, location.lat = get_geocoder_location_data(apikey, address)
        location.save()
    except Exception:
        return None