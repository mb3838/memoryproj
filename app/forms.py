from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, \
    TextAreaField, TimeField, SelectField
from flask_wtf.file import FileField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, \
    Length
from wtforms.fields import DateField
from app.models import User


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')


class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Request Password Reset')


class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    submit = SubmitField('Submit')

    def __init__(self, original_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError('Please use a different username.')


class EmptyForm(FlaskForm):
    submit = SubmitField('Submit')


class EventForm(FlaskForm):
    name = StringField('Event Name', [DataRequired()])
    location = StringField('Event Address', [DataRequired()], id='autocompleteOrigin')
    date = DateField('Date', format='%Y-%m-%d')
    time = TimeField('Event Start')
    live_log = SubmitField('Log Live Event')

class RouteForm(FlaskForm):
    origin = StringField('Start Address', [DataRequired()], id='autocompleteOrigin')
    destination = StringField('Event Address', [DataRequired()], id='autocompleteDestination')
    mode_choices = [('walking', 'Walking'), ("driving", 'Driving'), ('transit', 'Transit'),
    ('bicycling', 'Bicycling')]
    mode = SelectField('Transport Mode', choices=mode_choices)
    submit = SubmitField('Confirm')