import os, pathlib
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['your-email@example.com']
    MAX_CONTENT_LENGTH = 1024 * 1024
    UPLOAD_EXTENSIONS = ['.jpg', '.png', '.gif']
    UPLOAD_PATH = str(pathlib.Path().absolute()) + r"/app/static/uploads"
    POSTS_PER_PAGE = 12
    S3_BUCKET = "captured-videos-typ"
    S3_KEY = "AKIAXVGGIKKLMCGB42TE"
    S3_SECRET = "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"
    S3_LOCATION = 'http://{}.s3.amazonaws.com/'.format(S3_BUCKET)