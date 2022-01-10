from datetime import datetime
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, \
    EmptyForm, ResetPasswordRequestForm, ResetPasswordForm, EventForm, LiveLogForm
from app.editing import streetview
from app.output import slides
from app.models import User, Event, Log
from app.email import send_password_reset_email


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
        url = 'http://freegeoip.net/json/{}?apikey=7e033be0-70b2-11ec-a63a-a5f43bf3eadd'.format(request.remote_addr)
        r = requests.get(url)
        j = json.loads(r.text)
        city = j['city']

        print(city)
        event = Event(name=form.name.data, location=form.location.data)
        db.session.add(event)
        db.session.commit()
        db.session.refresh(event)
        if 'live_log' in request.form:
            return redirect(url_for('live_log', event_id=event.id))
        elif 'plan' in request.form:
            return redirect(url_for('plan'))
    return render_template('create_event.html', title='Create Event', form=form)

@app.route('/live_log/<event_id>', methods=['GET', 'POST'])
def live_log(event_id):
    form = LiveLogForm()
    if form.validate_on_submit():
        if 'log' in request.form:
            log = Log(event_id=event_id)
            db.session.add(log)
            db.session.commit()
            flash('Logged')
        elif 'generate' in request.form:
            streetview.SaveViews(event_id)
            return redirect(url_for('slideshow', event_id=event_id))
    return render_template('live_log.html', title='Live Log', form=form)

@app.route('/plan')
def plan():
    
    return render_template('create_event.html', title='Register')

@app.route('/slideshow/<event_id>', methods=['GET'])
def slideshow(event_id):
    current_event = Event.query.filter_by(id=event_id).first()

    filepath = 'streetview_images/' + current_event.location + '.jpg'
    return render_template('slideshow.html', title='Slideshow', location=current_event.location, filepath=filepath)