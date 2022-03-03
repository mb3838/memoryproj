import json, googlemaps, requests, pandas as pd, numpy as np, \
	polyline, urllib, math, os, pathlib, glob, subprocess, cv2

PHOTO_FOLDER = str(pathlib.Path().absolute()) + r"/app/static/route_images"
VIDEO_FOLDER = str(pathlib.Path().absolute()) + r"/app/static/route_video"


def createRouteVid(orig, dest, mode, event_id):
	gmaps = googlemaps.Client(key='AIzaSyAwAj6vhSVeS0JpxKs610ydB3ONQtEpYPY')
	# turn addresses into lat long values
	orig_lat, orig_long = getLatLong(orig)
	dest_lat, dest_long = getLatLong(dest)
	origin = (orig_lat, orig_long)
	destination = (dest_lat, dest_long)

	print("lat, lng origin: ", origin, "\n")
	print("lat, lng dest: ", destination, "\n")

	# call google directions api
	directions = gmaps.directions(origin=origin, destination=destination, mode=mode)

	# grab certain amount of waypoints on the route
	all_path_points = polyline.decode(directions[0]['overview_polyline']['points'])
	# create dense gps pinpointed route - to then pick from & shorten
	dense_points = [interpolate_points(pt[0],pt[1],hop_size=1) for pt in zip(all_path_points[:-1],all_path_points[1:])]
	look_points_rough = [item for sequence in dense_points for item in sequence]
	# Remove unnecessary/duplicate points
	look_points = clean_look_points(look_points_rough)

	# create dataframe of points - location, compass direciton heading
	route_df = create_df(look_points)


	total_pins = len(route_df)
	# get step distance for a 60 sec video - 1 image per second
	step_hop = total_pins//60
	print("Total points = ", total_pins, "\n")
	print("pins/60 = ", step_hop, " a second\n")
	# get every nth step of the route - depending on how many steps in total (1 min video)
	chosen_points = route_df.iloc[::step_hop, :]
	print("Stepped total points = ", chosen_points, "\n")
	# use polyline to pin the location of these steps 

	# find compass direction for each gps point 

	# save streetview image of each point
	get_images(chosen_points)
	# compile the photos in the folder to a video
	create_video(event_id)
	# delete photos from folder once finished with them
	files = glob.glob(PHOTO_FOLDER + '/*.jpg')
	for f in files:
		os.remove(f)
	print("\ndone\n")
	


def getLatLong(address):

	params = {
		'key': 'AIzaSyAwAj6vhSVeS0JpxKs610ydB3ONQtEpYPY',
		'address': address
	}

	base_url = "https://maps.googleapis.com/maps/api/geocode/json?"
	response = requests.get(base_url, params=params).json()

	if response['status'] == 'OK':
		geometry_repsonse = response['results'][0]['geometry']
		lat = geometry_repsonse['location']['lat']
		lng = geometry_repsonse['location']['lng']
	return lat, lng



# Given two GPS points (lat/lon), interpolate a sequence of GPS points in a straight line
def interpolate_points(a_gps,b_gps,n_points=10,hop_size=None):
	if hop_size is not None:
		distance = haversine(a_gps, b_gps)
		n_points = np.ceil(distance*1.0/hop_size)
	x = np.linspace(a_gps[0],b_gps[0],int(n_points))
	y = np.linspace(a_gps[1],b_gps[1],int(n_points))
	dense_points_list = zip(x,y)
	return dense_points_list
	# else:
	#	 print("You forgot to provide a hop parameter! Choose between:")
	#	 print("  n_points = number of points to interpolate;")
	#	 print("  hop_size = maximum distance between points in meters.")


def haversine(a_gps, b_gps):
	
	# Calculate the great circle distance between two points 
	# on the earth (specified in decimal degrees)
	
	lat1, lon1 = a_gps
	lat2, lon2 = b_gps
	# convert decimal degrees to radians 
	lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
	# haversine formula 
	dlon = lon2 - lon1 
	dlat = lat2 - lat1 
	a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
	c = 2 * math.asin(math.sqrt(a)) 
	km = 6367 * c
	m = 6367000.0 * c
	return m

def clean_look_points(look_points):
	# Remove points that are the same
	pt_diffs = [np.array(a)-np.array(b) for (a,b) in zip(look_points[:-1],look_points[1:])]
	keepers = np.abs(np.array(pt_diffs))>0
	look_points_out = [look_points[i] for i in range(len(keepers)) if np.any(keepers[i])]
	return look_points_out


def create_df(gps_points):
	# Create dataframe with GPS points
	pt_list = pd.DataFrame(index=range(len(gps_points)), columns=["lat", "lon", "heading"])
	lats, lons = zip(*gps_points)
	pt_list['lat'] = lats
	pt_list['lon'] = lons
	# Compute basic headings
	headings = [calculate_initial_compass_bearing(pt[0], pt[1]) for pt in zip(gps_points[:-1],gps_points[1:])]
	pt_list['heading'] = headings + [headings[-1]]
	return pt_list


# Gist copied from https://gist.github.com/jeromer/2005586 which is in the public domain:
def calculate_initial_compass_bearing(pointA, pointB):
	if (type(pointA) != tuple) or (type(pointB) != tuple):
		raise TypeError("Only tuples are supported as arguments")
	lat1 = math.radians(pointA[0])
	lat2 = math.radians(pointB[0])
	diffLong = math.radians(pointB[1] - pointA[1])
	x = math.sin(diffLong) * math.cos(lat2)
	y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1)
			* math.cos(lat2) * math.cos(diffLong))
	initial_bearing = math.atan2(x, y)
	initial_bearing = math.degrees(initial_bearing)
	compass_bearing = (initial_bearing + 360) % 360
	return compass_bearing


def get_images(df):
	i = 1
	for index, row in df.iterrows():
		download_streetview_image(i, row['lat'], row['lon'], row['heading'])
		i += 1

# Usage example:
# >>> download_streetview_image((46.414382,10.012988))
def download_streetview_image(index, lat, lon, heading):
	savepath = PHOTO_FOLDER
	picsize="600x300"
	pitch=-0
	fov=90
	radius=5
	assert type(radius) is int
	if(index < 10):
		index = "0{}".format(index)
	filename = "image-{0}.jpg".format(index)
	lat_lng_str = str(lat) + "," + str(lon)
	# Any size up to 640x640 is permitted by the API
	# fov is the zoom level, effectively. Between 0 and 120.
	base = "https://maps.googleapis.com/maps/api/streetview?"
	url = base + "size=" + picsize + "&location=" + lat_lng_str + "&heading=" + str(heading) + "&pitch=" + str(pitch) + "&fov=" + str(fov) + "&source=outdoor" + "&radius" + str(radius) + "&key=" + 'AIzaSyAwAj6vhSVeS0JpxKs610ydB3ONQtEpYPY'

	urllib.request.urlretrieve(url, os.path.join(savepath,filename))


def create_video(event_id):
	img_array = []
	for filename in sorted(glob.glob(PHOTO_FOLDER + '/*.jpg')):
		img = cv2.imread(filename)
		height, width, layers = img.shape
		size = (width,height)
		img_array.append(img)

	out = cv2.VideoWriter(VIDEO_FOLDER + '/route_{0}.mp4'.format(event_id),cv2.VideoWriter_fourcc(*'AVC1'), 1, size)
	
	for i in range(len(img_array)):
		out.write(img_array[i])
	out.release()
	