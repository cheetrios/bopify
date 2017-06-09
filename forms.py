"""
__name__		= forms.py
__author__	    = Cheetrios
__description__ = Forms object file used by Flask to process also POST
events from forms on the pages
"""

from flask_wtf import Form
from wtforms import StringField
from wtforms.validators import DataRequired

class CreateForm(Form):
    session = StringField('session')
    genre   = StringField('genre')

class JoinForm(Form):
    session = StringField('session')