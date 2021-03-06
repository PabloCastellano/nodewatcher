# -*- coding: utf-8 -*-
#
# Development Django settings for your network nodewatcher

import os.path
settings_dir = os.path.abspath(os.path.dirname(__file__))
database_file = os.path.join(settings_dir, 'db.sqlite')
default_template_dir = os.path.join(settings_dir, 'templates')
locale_dir = os.path.join(settings_dir, 'locale')
geoip_dir = os.path.abspath(os.path.join(settings_dir, '..', 'geoip'))
static_dir = os.path.abspath(os.path.join(settings_dir, '..', 'static'))

import djcelery
djcelery.setup_loader()

DEBUG = True
TEMPLATE_DEBUG = DEBUG

# A tuple that lists people who get code error notifications. When
# DEBUG=False and a view raises an exception, Django will e-mail these
# people with the full exception information. Each member of the tuple
# should be a tuple of (Full name, e-mail address).
ADMINS = ()

MANAGERS = ADMINS

DATABASES = {
  'default' : {
    'ENGINE'   : 'django.db.backends.sqlite3', # 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
    'NAME'     : database_file, # Or path to database file if using sqlite3.
    'USER'     : '',            # Not used with sqlite3.
    'PASSWORD' : '',            # Not used with sqlite3.
    'HOST'     : '',            # Set to empty string for localhost. Not used with sqlite3.
    'PORT'     : '',            # Set to empty string for default. Not used with sqlite3.
  },
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Ljubljana'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html and
# http://docs.djangoproject.com/en/dev/topics/i18n/#term-language-code
LANGUAGE_CODE = 'en'

_ = lambda s: s # Dummy function so that makemessages finds it
LANGUAGES = (
  ('en', _('English')),
)

LOCALE_PATHS = (
  locale_dir,
)

GEOIP_PATH = geoip_dir
DEFAULT_COUNTRY = 'SI'

URL_VALIDATOR_USER_AGENT = 'Django'

# Date input formats below take as first argument day and then month in x/y/z format
DATE_INPUT_FORMATS = (
  '%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y', '%b %d %Y',
  '%b %d, %Y', '%d %b %Y', '%d %b, %Y', '%B %d %Y',
  '%B %d, %Y', '%d %B %Y', '%d %B, %Y',
)

# All those formats are only defaults and are localized for users
DATE_FORMAT = 'd/M/Y'
TIME_FORMAT = 'H:i'
DATETIME_FORMAT = 'd/M/Y, H:i:s'
YEAR_MONTH_FORMAT = 'F Y'
MONTH_DAY_FORMAT = 'j F'
SHORT_DATE_FORMAT = 'd/m/y'
SHORT_DATETIME_FORMAT = 'd/m/y H:i'
FIRST_DAY_OF_WEEK = 1
DECIMAL_SEPARATOR = '.'
THOUSAND_SEPARATOR = ','
NUMBER_GROUPING = 0

# We override defaults
FORMAT_MODULE_PATH = 'frontend.formats'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = static_dir

# URL that handles the media served from MEDIA_ROOT. Make sure to always
# use a trailing slash.
# Examples: "http://media.lawrence.com/", "http://example.net/media/"
MEDIA_URL = '/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Set to true if you want https instead of http in sitemaps' and feeds' URLs
SITEMAPS_USE_HTTPS = False
FEEDS_USE_HTTPS = False
# In general use https when constructing full URLs to nodewatcher?
USE_HTTPS = False

# Make this unique, and don't share it with anybody.
SECRET_KEY = '1p)^zvjul0^c)v5*l!8^48g=ili!cn54^l)wl1avvu-x$==k7p'

# Google Maps API key for 127.0.0.1
GOOGLE_MAPS_API_KEY = 'ABQIAAAAsSAo-sxy6T5T7_DN1d9N4xRi_j0U6kJrkFvY4-OX2XYmEAa76BRH5tgaUAj1SaWR_RbmjkZ4zO7dDA'

# Where the map displaying all nodes is initially positioned
# Where the map is initially positioned when adding a new node is configured for each project in the database
GOOGLE_MAPS_DEFAULT_LAT = 46.17
GOOGLE_MAPS_DEFAULT_LONG = 14.96
GOOGLE_MAPS_DEFAULT_ZOOM = 8
GOOGLE_MAPS_DEFAULT_NODE_ZOOM = 15 # Zoom to use when displaying one node

NETWORK_NAME = 'your network name' # You probably want to configure your site name the same
NETWORK_HOME = 'http://example.net'
NETWORK_CONTACT = 'open@example.net'
NETWORK_CONTACT_PAGE = 'http://example.net/contact'
NETWORK_DESCRIPTION = 'open wireless network in your neighborhood'

#Use NETWORK_FAVICON_URL if you want to set a favicon included in HTML
#NETWORK_FAVICON_URL = MEDIA_URL + 'images/favicon.ico'

#Use NETWORK_LOGO_URL if you want to set an image logo instead of the network name in the header
#NETWORK_LOGO_URL = MEDIA_URL + 'images/logo.png'

# For local development it is better to send all e-mails to console
# Disable for production use and e-mails will be really send to users
# With version 1.2 Django supports e-mail backends which can be used instead of this
EMAIL_TO_CONSOLE = True

EMAIL_HOST = 'localhost'
# For backwards compatibility (before it was possible to configure password reset
# subject through a template) we also format subject prefix through internationalization
EMAIL_SUBJECT_PREFIX = '[' + NETWORK_NAME + '] ' # Prefix is defined also in some subject templates
EMAIL_EVENTS_SENDER = 'events@example.net'
EMAIL_IMAGE_GENERATOR_SENDER = 'generator@example.net'
DEFAULT_FROM_EMAIL = 'webmaster@example.net'
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Configure with your bit.ly and Twitter user data to enable tweets via Twitther for some network events
#BITLY_LOGIN = "Your bit.ly login"
#BITLY_API_KEY = "Your bit.ly API key"
#TWITTER_USERNAME = "Your Twitter username"
#TWITTER_PASSWORD = "Your Twitter password"

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
  'django.template.loaders.filesystem.Loader',
  'django.template.loaders.app_directories.Loader',
#  'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
  'django.contrib.auth.context_processors.auth',
  'django.core.context_processors.debug',
  'django.core.context_processors.i18n',
  'django.core.context_processors.media',
  'django.contrib.messages.context_processors.messages',
  'frontend.nodes.context_processors.web_client_node',
  'frontend.nodes.context_processors.global_values',
)

MIDDLEWARE_CLASSES = (
  'django.middleware.common.CommonMiddleware',
  'django.contrib.sessions.middleware.SessionMiddleware',
  'django.middleware.csrf.CsrfViewMiddleware',
  'django.contrib.auth.middleware.AuthenticationMiddleware',
  'django.contrib.messages.middleware.MessageMiddleware',
  'django.middleware.transaction.TransactionMiddleware',
)

ROOT_URLCONF = 'frontend.urls'

TEMPLATE_DIRS = (
  # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
  # Always use forward slashes, even on Windows.
  # Don't forget to use absolute paths, not relative paths.
  default_template_dir,
)

FORCE_SCRIPT_NAME = ''

LOGIN_REDIRECT_URL = '/my/nodes/'
LOGIN_URL = '/account/login/'
LOGOUT_URL = '/account/logout/'

AUTH_PROFILE_MODULE = 'account.UserProfileAndSettings'

ACCOUNT_ACTIVATION_DAYS = 7
REGISTRATION_OPEN = True

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

CSRF_FAILURE_VIEW = 'frontend.nodes.views.forbidden_view'

# We support some common password formats to ease transition
AUTHENTICATION_BACKENDS = (
  'frontend.account.auth.ModelBackend',
  'frontend.account.auth.AprBackend',
  'frontend.account.auth.CryptBackend',
)

INSTALLED_APPS = (
  'django.contrib.auth',
  'django.contrib.contenttypes',
  'django.contrib.sessions',
  'django.contrib.sites',
  'django.contrib.messages',
  'django.contrib.sitemaps',
  'djcelery',
  'registration',
  'south',
  'frontend.nodes',
  'frontend.generator',
  'frontend.account',
  'frontend.dns',
  'frontend.policy',
  'frontend.monitor',
)

# External programs configuration
# If you have programs installed in exotic locations you can specify them here
#GRAPHVIZ_BIN = '/path/to/neato'
#FPING_BIN = '/path/to/fping'

# Graph configuration
GRAPH_DIR = os.path.join(MEDIA_ROOT, 'graphs')
GRAPH_TIMESPAN_PREFIXES = ('day', 'week', 'month', 'year')
GRAPH_TIMESPANS = {
  'day'   : 86400,
  'week'  : 604800,
  'month' : 2678400,
  'year'  : 33053184,
}

# Monitor configuration
MONITOR_WORKDIR = os.path.abspath(os.path.join(settings_dir, '..', 'monitor')) # Absolute path to directory containing monitor.py file
MONITOR_WORKERS = 1 # Should be increased to much more (like 20) if your database can support simultaneous connections (SQLite does not)
MONITOR_GRAPH_WORKERS = 5
MONITOR_POLL_INTERVAL = 300
MONITOR_OLSR_HOST = '127.0.0.1' # A host with OLSR txt-info plugin running
MONITOR_LOGFILE = os.path.join(MONITOR_WORKDIR, 'monitor.log')

# Data archive configuration
DATA_ARCHIVE_ENABLED = False
DATA_ARCHIVE_HOST = '127.0.0.1'
DATA_ARCHIVE_PORT = 27017
DATA_ARCHIVE_DB = 'nodewatcher'

# Is image generator enabled or not. If set to False the pybeanstalk dependency is not needed.
IMAGE_GENERATOR_ENABLED = False
# Is image generator temporary suspended (like because firmware image it would produce contains errors)?
# If it is, image requests are not queued and message about that is issued to the user
IMAGE_GENERATOR_SUSPENDED = False
# If you want to change the ownership of image files after they have been generated, set the username here
IMAGE_GENERATOR_USER = None

IMAGES_BINDIST_URL = 'http://example.net/images/'

# Are non-staff members allowed to mark a node as a border router
NONSTAFF_BORDER_ROUTERS = False

# Cache backend (used by on-demand graph generation, too)
CACHE_BACKEND = 'locmem://'

# Celery
BROKER_BACKEND = "mongodb"
BROKER_HOST = "localhost"
BROKER_PORT = 27017
BROKER_VHOST = "nodewatcher"
CELERYD_PREFETCH_MULTIPLIER = 15
CELERY_IGNORE_RESULT = True

# Enabling the on-demand graph generation requires a working Celery broker
# configuration and a celeryd daemon running in the background to dispatch
# tasks that generate graphs. Simply enabling this option without proper
# configuration/setup will not work.
ENABLE_GRAPH_DISPLAY = False

DOCUMENTATION_LINKS = {
#  'custom_node'          : 'http://example.net/wiki/CustomNode',
#  'known_issues'         : 'http://example.net/wiki/KnownIssues',
#  'report_issue'         : 'http://example.net/newticket',
  'diversity'            : 'http://en.wikipedia.org/wiki/Antenna_diversity',
  'decimal_degrees'      : 'http://en.wikipedia.org/wiki/Decimal_degrees',
  'ip_address'           : 'http://en.wikipedia.org/wiki/IP_address',
#  'solar'                : 'http://example.net/wiki/Solar',
  'antenna_type'         : 'http://en.wikipedia.org/wiki/Antenna_%28radio%29',
  'antenna_polarization' : 'http://en.wikipedia.org/wiki/Antenna_%28radio%29#Polarization',
  'vpn'                  : 'http://en.wikipedia.org/wiki/Virtual_private_network',
  'snr'                  : 'http://en.wikipedia.org/wiki/Signal-to-noise_ratio',
  'bitrate'              : 'http://en.wikipedia.org/wiki/Bit_rate',
}
