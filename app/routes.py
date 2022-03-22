from datetime import datetime
import mimetypes
from flask import render_template, flash, redirect, url_for, request, send_from_directory, abort, Response, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from werkzeug.utils import secure_filename
from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, \
    EmptyForm, ResetPasswordRequestForm, ResetPasswordForm, EventForm,\
    RouteForm
from app.editing import streetview, routeVideo
from app.output import slides
from app.models import User, Event, Log
from app.email import send_password_reset_email
import requests, os, imghdr, time, pathlib
#from camera import VideoCamera
from threading import Thread
import boto3, botocore
from botocore.client import Config
import numpy as np

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpegs', 'gif', 'jpeg'])

s3 = boto3.client(
   "s3",
   region_name='eu-west-2',
   aws_access_key_id=app.config['S3_KEY'],
   aws_secret_access_key=app.config['S3_SECRET']
)

def upload_file_to_s3(file, bucket_name, acl="public-read"):
    try:
        s3.upload_fileobj(
            file,
            bucket_name,
            file.filename,
            ExtraArgs={
                "ACL": acl,
                "ContentType": file.content_type
            }
        )
    except Exception as e:
        print("Something Happened: ", e)
        return e
    return "{}{}".format('http://{}.s3.amazonaws.com/'.format(bucket_name), file.filename)

def get_bucket_keys(bucket):
    keys = []
    resp = s3.list_objects_v2(Bucket=bucket)
    try:
        for obj in resp['Contents']:
            keys.append(obj['Key'])
        return keys
    except:
        return []
    
def find_event_files(bucket, event_id):
    keys = get_bucket_keys(bucket)
    event_keys = []
    for key in keys:
        dash = key.rfind('-')
        dot = key.rfind('.')
        if key[dash+1:dot] == str(event_id):
            event_keys.append(key) 
    return event_keys

def download_file(bucket, key, save_location):
    print('trying to find: ', key, ' in bucket: ', bucket)
    s3.download_file(bucket, key, save_location)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

def validate_image(stream):
    header = stream.read(512)
    stream.seek(0)
    format = imghdr.what(None, header)
    if not format:
        return None
    return '.' + (format if format != 'jpeg' else 'jpg')

@app.template_filter('format_date')
def format_date(timestamp):
    date = timestamp.date()
    return date

@app.errorhandler(413)
def too_large(e):
    return "File is too large", 413

@app.route('/', methods=['GET', 'POST'])
@app.route('/index')
@login_required
def index():
    return render_template('index.html', title='Home')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset your password')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html',
                           title='Reset Password', form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)


@app.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    form = EmptyForm()
    return render_template('user.html', user=user, form=form)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)

@app.route('/create_event', methods=['GET', 'POST'])
@login_required
def create_event():
    form = EventForm()
    if form.validate_on_submit():
        
        # add new event to db
        event = Event(user_id=current_user.id, name=form.name.data, location=form.location.data, date=form.date.data, start=form.time.data)
        db.session.add(event)
        db.session.commit()
        db.session.refresh(event)
        streetview.SaveViews(event.id)

        #send to s3
        filepath = 'app/static/streetview_images/' + form.location.data + '.jpg'
        s3.upload_file(filepath,'event-location-images-typ',form.location.data + '.jpg')

        if 'live_log' in request.form:
            return redirect(url_for('live_log', event_id=event.id))
        elif 'plan' in request.form:
            return redirect(url_for('plan'))
    return render_template('create_event.html', title='Create Event', form=form)

@app.route('/live_log/<event_id>', methods=['GET', 'POST'])
def live_log(event_id):
    current_event = Event.query.filter_by(id=event_id).first()
    if request.method == "POST":
        if 'log' in request.form:
            log = Log(event_id=event_id)
            db.session.add(log)
            db.session.commit()
            flash('Logged')
        elif 'save' in request.form:
            return redirect(url_for('dashboard', event_id=event_id))
    return render_template('live_log.html', title='Live Log', event_id=event_id, name=current_event.name)

@app.route('/live_log/<event_id>/requests',methods=['POST'])
def sendVideo(event_id):
    if 'video-blob' not in request.files:
        resp = jsonify({'message' : 'No video in the request'})
        resp.status_code = 400
        return resp
    vid = request.files['video-blob']
    print("vid response = ", vid)
    print("vid name = ", vid.filename)
    vid.filename = secure_filename(vid.filename)
    output = upload_file_to_s3(vid, app.config["S3_BUCKET"])
    print("response from sending to s3 = ", output)
    return redirect(url_for('live_log', event_id=event_id))

@app.route('/dashboard/<event_id>', methods=['GET'])
def dashboard(event_id):
    current_event = Event.query.filter_by(id=event_id).first()
    address = current_event.location

    #create dictionaries of all the event media files needed for this event
    imgs = {
        'bucket': 'uploaded-images-typ',
        'filepath': 'app/static/uploads/',
        'keys': find_event_files('uploaded-images-typ', event_id)
    }
    uploaded_vids = {
        'bucket': 'uploaded-videos-typ',
        'filepath': 'app/static/vid_uploads/',
        'keys': find_event_files('uploaded-videos-typ', event_id)
    }
    captured_vids = {
        'bucket': 'captured-videos-typ',
        'filepath': 'app/static/captured-video/',
        'keys': find_event_files('captured-videos-typ', event_id)
    }
    route_vid = {
        'bucket': 'route-videos-typ',
        'filepath': 'app/static/route_video/',
        'keys': find_event_files('route-videos-typ', event_id)
    }
    location_img = {
        'bucket': 'event-location-images-typ',
        'filepath': 'app/static/streetview_images/',
        'keys': [address + '.jpg']
    }

    required_media = {
        'imgs': imgs,
        'uploaded-vids': uploaded_vids,
        'route': route_vid,
        'captured-vids': captured_vids,
        'location-img': location_img
    }

    # for each required file - if it cant be found on device - download from s3
    for key in required_media:
        for file in required_media[key]['keys']:
            if os.path.isfile(required_media[key]['filepath'] + file) == False:
                print('file not found: ', file)
                download_file(required_media[key]['bucket'], file, required_media[key]['filepath'] + file)

    loc_img_filepath = 'streetview_images/' + current_event.location + '.jpg'
    route_vid_name = "route-" + str(current_event.id) + ".mp4"
    uploaded_img_filenames = imgs['keys']
    uploaded_vid_filenames = uploaded_vids['keys']
    captured_vid_filenames = captured_vids['keys']
    captured_vid_len = len(captured_vid_filenames)
    
    geo = address.rfind(",", 0, address.rfind(","))
    geo = address[geo + 2:].replace(" ","")
    
    url = 'https://api.openweathermap.org/data/2.5/weather?q={}&appid=0fda3beb7131e56f9a92e555917cdd76'.format(geo)
    print(url)
    try:
        response = requests.get(url)
        json = response.json()
        city_id = json['id']
        print("cityid = ", city_id)
    except ValueError:
        city_id = 2172797
        print("No JSON returned")

    #return list of filenames
    return render_template('dashboard.html', title='Dashboard', location=current_event.location, city_id=city_id, event_id=event_id, event_name=current_event.name,
    time=str(current_event.start)[:-3], date=current_event.date, route_vid_name=route_vid_name, location_image_fp=loc_img_filepath, uploaded_img_filenames=uploaded_img_filenames, 
    captured_vid_filenames=captured_vid_filenames, captured_vid_len=captured_vid_len, uploaded_vid_filenames = uploaded_vid_filenames)

@app.route('/image_upload/<event_id>', methods=['GET', 'POST'])
def image_upload(event_id):
    files = os.listdir(app.config['UPLOAD_PATH'])
    if request.method == 'POST':
        uploaded_file = request.files.get('file', None)
        splitName = os.path.splitext(uploaded_file.filename)
        uploaded_file.filename = secure_filename(splitName[0] + "-" + event_id + splitName[1])
        if uploaded_file.filename != '':
            file_ext = os.path.splitext(uploaded_file.filename)[1]
            if file_ext not in app.config['UPLOAD_EXTENSIONS']or \
                    file_ext != validate_image(uploaded_file.stream):
                return "Invalid image", 400
            output = upload_file_to_s3(uploaded_file, "uploaded-images-typ")
            print("response from sending to s3 = ", output)
    return render_template('image_upload.html', title='Upload image', files=files, event_id=event_id)


@app.route('/image_upload/<filename>')
@login_required
def upload(filename):
    
    return send_from_directory(os.path.join(app.config['UPLOAD_PATH'],
    current_user.get_id()), filename)


@app.route('/video_upload/<event_id>', methods=['GET', 'POST'])
def video_upload(event_id):
    files = os.listdir(app.config['VID_UPLOAD_PATH'])
    if request.method == 'POST':
        uploaded_file = request.files.get('file', None)
        splitName = os.path.splitext(uploaded_file.filename)
        uploaded_file.filename = secure_filename(splitName[0] + "-" + event_id + splitName[1])
        if uploaded_file.filename != '':
            file_ext = os.path.splitext(uploaded_file.filename)[1]
            if file_ext not in app.config['VID_UPLOAD_EXTENSIONS']:
                return "Invalid video", 400
            output = upload_file_to_s3(uploaded_file, "uploaded-videos-typ")
            print("response from sending to s3 = ", output)
    return render_template('video_upload.html', title='Upload Video', files=files, event_id=event_id)


@app.route('/video_upload/<filename>')
@login_required
def vid_upload(filename):
    
    return send_from_directory(os.path.join(app.config['VID_UPLOAD_PATH'],
    current_user.get_id()), filename)


@app.route('/past_events', methods=['GET', 'POST'])
@login_required
def past_events():
    page = request.args.get('page', 1, type=int)
    events = Event.query.filter_by(user_id=current_user.id).order_by(Event.timestamp.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'])
    next_url = url_for('past_events', page=events.next_num) \
        if events.has_next else None
    prev_url = url_for('past_events', page=events.prev_num) \
        if events.has_prev else None
    return render_template('past_events.html', title='Past Events', events=events,
    next_url=next_url, prev_url=prev_url)

@app.route('/delete/<event_id>', methods=['GET', 'POST'])
@login_required
def delete_event(event_id):
    event = Event.query.filter_by(id=event_id).first()
    logs = Log.query.filter_by(event_id=event_id).all()
    if event:
        msg_text = 'Event %s successfully removed' % str(event.name)
        db.session.delete(event)
        db.session.commit()
        flash(msg_text)
    return redirect(url_for('past_events'))

@app.route('/route/<event_id>', methods=['GET', 'POST'])
@login_required
def route(event_id):
    form = RouteForm()
    if form.validate_on_submit():
        origin = form.origin.data
        destination = form.destination.data
        mode = form.mode.data
        print('origin = ', origin, "\n")
        print('destination = ', destination, "\n")
        print('mode = ', mode, "\n")
        routeVideo.createRouteVid(origin, destination, mode, event_id)
        #send to s3
        filename = 'route-' + str(event_id) + '.mp4'
        filepath = 'app/static/route_video/' + filename
        try:
            s3.upload_file(filepath,'route-videos-typ',filename)
        except FileNotFoundError:
            print("File ", filename, " not found")
        flash('Route uploaded!')

    return render_template('route.html', title='Event Route', form=form,
    event_id = event_id)

