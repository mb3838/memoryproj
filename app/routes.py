from datetime import datetime
import mimetypes
from flask import render_template, flash, redirect, url_for, request, send_from_directory, abort, Response, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from werkzeug.utils import secure_filename
from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, \
    EmptyForm, ResetPasswordRequestForm, ResetPasswordForm, EventForm,\
    LiveLogForm, RouteForm
from app.editing import streetview, routeVideo
from app.output import slides
from app.models import User, Event, Log, Images
from app.email import send_password_reset_email
import requests, os, imghdr, time, pathlib
#from camera import VideoCamera
from threading import Thread
import cv2
import numpy as np

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpegs', 'gif'])

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

        if 'live_log' in request.form:
            return redirect(url_for('live_log', event_id=event.id))
        elif 'plan' in request.form:
            return redirect(url_for('plan'))
    return render_template('create_event.html', title='Create Event', form=form)

@app.route('/live_log/<event_id>', methods=['GET', 'POST'])
def live_log(event_id):
    current_event = Event.query.filter_by(id=event_id).first()
    form = LiveLogForm()
    if form.validate_on_submit():
        if 'log' in request.form:
            log = Log(event_id=event_id)
            db.session.add(log)
            db.session.commit()
            flash('Logged')
        elif 'generate' in request.form:
            return redirect(url_for('dashboard', event_id=event_id))
    return render_template('live_log.html', title='Live Log', form=form, event_id=event_id, name=current_event.name)

@app.route('/plan')
def plan():
    
    return render_template('create_event.html', title='Register')

@app.route('/dashboard/<event_id>', methods=['GET'])
def dashboard(event_id):
    current_event = Event.query.filter_by(id=event_id).first()

    address = current_event.location
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

    filepath = 'streetview_images/' + current_event.location + '.jpg'
    video_name = "route_" + str(current_event.id) + ".mp4"
    #query images table for matching event_id's
    filelist = Images.query.filter_by(event_id=event_id).all()
    #return list of filenames
    return render_template('dashboard.html', title='Dashboard', location=current_event.location, 
    filepath=filepath, city_id=city_id, filenames=filelist, event_id=event_id, event_name=current_event.name,
    time=str(current_event.start)[:-3], date=current_event.date, video_name = video_name)

@app.route('/image_upload/<event_id>', methods=['GET', 'POST'])
def image_upload(event_id):
    files = os.listdir(app.config['UPLOAD_PATH'])
    if request.method == 'POST':
        uploaded_file = request.files.get('file', None)
        splitName = os.path.splitext(uploaded_file.filename)
        filename = secure_filename(splitName[0] + "_" + event_id + splitName[1])
        if filename != '':
            file_ext = os.path.splitext(filename)[1]
            if file_ext not in app.config['UPLOAD_EXTENSIONS']or \
                    file_ext != validate_image(uploaded_file.stream):
                return "Invalid image", 400
            uploaded_file.save(os.path.join(app.config['UPLOAD_PATH'], filename))
    return render_template('image_upload.html', title='Upload image', files=files, event_id=event_id)


@app.route('/image_upload/<filename>')
@login_required
def upload(filename):
    
    return send_from_directory(os.path.join(app.config['UPLOAD_PATH'],
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
    images = Images.query.filter_by(event_id=event_id).all()
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
        flash('Route uploaded!')

    return render_template('route.html', title='Event Route', form=form,#
    event_id = event_id)


###################################VIDEO

global capture,rec_frame, switch, face, rec, out 
capture=0
face=0
switch=1
rec=0
rec_frame=None

#make shots directory to save pics
try:
    os.mkdir('./shots')
except OSError as error:
    pass

#Load pretrained face detection model   
txt_path = str(pathlib.Path().absolute()) + r"/app/static/face_recognition_model/deploy.prototxt.txt" 
model_path = str(pathlib.Path().absolute()) + r"/app/static/face_recognition_model/res10_300x300_ssd_iter_140000.caffemodel" 
net = cv2.dnn.readNetFromCaffe(os.path.relpath(txt_path), os.path.relpath(model_path))


camera = cv2.VideoCapture(0)

def record(out):
    global rec_frame
    while(rec):
        time.sleep(0.05)
        out.write(rec_frame)


def detect_face(frame):
    global net
    (h, w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0,
        (300, 300), (104.0, 177.0, 123.0))   
    net.setInput(blob)
    detections = net.forward()
    confidence = detections[0, 0, 0, 2]

    if confidence < 0.5:            
            return frame           

    box = detections[0, 0, 0, 3:7] * np.array([w, h, w, h])
    (startX, startY, endX, endY) = box.astype("int")
    try:
        frame=frame[startY:endY, startX:endX]
        (h, w) = frame.shape[:2]
        r = 480 / float(h)
        dim = ( int(w * r), 480)
        frame=cv2.resize(frame,dim)
    except Exception as e:
        pass
    return frame
 

def gen_frames():  # generate frame by frame from camera
    global out, capture,rec_frame
    while True:
        success, frame = camera.read() 
        if success:
            if(face):                
                frame= detect_face(frame)    
            if(capture):
                capture=0
                now = datetime.datetime.now()
                p = os.path.sep.join(['shots', "shot_{}.png".format(str(now).replace(":",''))])
                cv2.imwrite(p, frame)
            
            if(rec):
                rec_frame=frame
                frame= cv2.putText(cv2.flip(frame,1),"Recording...", (0,25), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255),4)
                frame=cv2.flip(frame,1)
            
                
            try:
                ret, buffer = cv2.imencode('.jpg', cv2.flip(frame,1))
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            except Exception as e:
                pass
                
        else:
            pass
    
    
@app.route('/live_log/<event_id>/video_feed')
def video_feed(event_id):
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/live_log/<event_id>/requests',methods=['POST','GET'])
def tasks(event_id):
    global switch,camera
    if request.method == 'POST':
        if request.form.get('click') == 'Capture':
            global capture
            capture=1
        elif  request.form.get('face') == 'Face Only':
            global face
            face=not face 
            if(face):
                time.sleep(4)   
        elif  request.form.get('stop') == 'Stop/Start':
            
            if(switch==1):
                switch=0
                camera.release()
                cv2.destroyAllWindows()
                
            else:
                camera = cv2.VideoCapture(0)
                switch=1
        elif  request.form.get('rec') == 'Start/Stop Recording':
            global rec, out
            rec= not rec
            if(rec):
                now=time.strftime("%Y-%m-%d_%H_%M_%S")
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                pth = os.path.join((str(pathlib.Path().absolute()) + r"/app/static/video"), 'vid_{}.avi'.format(now))
                out = cv2.VideoWriter(pth, fourcc, 20.0, (640, 480))
                #Start new thread for recording the video
                thread = Thread(target = record, args=[out,])
                thread.start()
            elif(rec==False):
                out.release()
                          
                 
    elif request.method=='GET':
        return redirect(url_for('live_log', event_id=event_id))
    return redirect(url_for('live_log', event_id=event_id))


if __name__ == '__main__':
    app.run()
    
camera.release()
cv2.destroyAllWindows() 





###net = cv2.dnn.readNetFromCaffe(url_for('static',filename='face_recognition_model/deploy.prototxt.txt'), url_for('static',filename='face_recognition_model/res10_300x300_ssd_iter_140000.caffemodel'))
