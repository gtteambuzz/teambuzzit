ROOT_URL = "http://main.teambuzz.org/"

VERSION = 1

import jinja2
import os
import string
import urllib
def finalize_value(value):
    return value if value is not None else ''
JINJA_ENVIRONMENT = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'views')), extensions=['jinja2.ext.autoescape'], autoescape=True, finalize=finalize_value)
def format_date(value, format='medium'):
    if format == 'medium':
        ret = value.strftime("%A, %B %d")
    elif format == 'short':
        ret = value.strftime("%b %d")
    else:
        ret = value.strftime(format)
    return string.replace(ret, " 0", " ")
def format_datetime(value, format='medium'):
    date = format_date(value, format)
    ret = date + ' at ' + value.strftime("%I:%M %p")
    return string.replace(ret, " 0", " ")
JINJA_ENVIRONMENT.filters['date'] = format_date
JINJA_ENVIRONMENT.filters['datetime'] = format_datetime
def urlencode(value):
    url_encoded_path = urllib.quote_plus(value)
    return url_encoded_path
JINJA_ENVIRONMENT.filters['urlencode'] = urlencode

import datetime
DATES = {
    'day_of': datetime.datetime(year=2015, month=10, day=18, hour=7, minute=30)
}

GREEK_AFFS = set(['Not Affiliated',
    'Alpha Epsilon Pi',
    'Alpha Phi',
    'Alpha Phi Alpha',
    'Alpha Tau Omega',
    'Beta Theta Pi',
    'Chi Psi',
    'Chi Phi',
    'Delta Chi',
    'Delta Sigma Phi',
    'Delta Tau Delta',
    'Delta Upsilon',
    'Kappa Alpha',
    'Kappa Alpha Psi Fraternity, Inc',
    'Kappa Sigma',
    'Lambda Chi Alpha',
    'Phi Delta Theta',
    'Phi Gamma Delta',
    'Phi Kappa Psi',
    'Phi Kappa Sigma',
    'Phi Kappa Tau',
    'Phi Kappa Theta',
    'Phi Sigma Kappa',
    'Pi Kappa Alpha',
    'Pi Kappa Phi',
    'Psi Upsilon',
    'Sigma Chi',
    'Sigma Nu',
    'Sigma Phi Epsilon',
    'Sigma Pi',
    'Tau Kappa Epsilon',
    'Theta Chi',
    'Theta Xi',
    'Alpha Chi Omega',
    'Alpha Delta Pi',
    'Alpha Gamma Delta',
    'Alpha Xi Delta',
    'Lambda Theta Alpha',
    'Chi Omega Tau',
    'Phi Mu',
    'Zeta Tau Alpha',
    'Lambda Nu',
    'Alpha Delta Chi',
    'Alpha Phi Omega',
    'Alpha Kappa Alpha',
    'Delta Sigma Theta',
    'Alpha Omega Epsilon',
    'Sigma Alpha Epsilon',
    'Zeta Beta Tau'
])

