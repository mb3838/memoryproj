import urllib, os, urllib.request, pathlib
from app import app, db
from app.models import User, Event, Log
from geopy.geocoders import Nominatim

#geolocator = Nominatim(user_agent = 'memoryproj')
myloc = str(pathlib.Path().absolute()) + r"\app\static\streetview_images" 


def GetStreet(address,SaveLoc):
    #location = geolocator.geocode(address, timeout=20)
    base = "https://maps.googleapis.com/maps/api/streetview?size=600x400&location="
    MyUrl = base + urllib.parse.quote_plus(address) + "&fov=180&heading=120&key=AIzaSyAwAj6vhSVeS0JpxKs610ydB3ONQtEpYPY"
    fileName = address + ".jpg"
    
    urllib.request.urlretrieve(MyUrl, os.path.join(SaveLoc,fileName))



def SaveViews(id):
    Tests = []
    event_id = Event.query.filter_by(id = id).first()
    Tests.append(str(event_id.location))

    for i in range(len(Tests)):
        GetStreet(Tests[i],myloc)
        #print(Tests[i])