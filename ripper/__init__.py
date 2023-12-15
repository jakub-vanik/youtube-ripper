#!/usr/bin/python3

import datetime
import flask
import flask_babel
import json
import werkzeug.middleware.proxy_fix

from . import main

app = flask.Flask(__name__)
app.config.from_file("config.json", load=json.load)
app.wsgi_app = werkzeug.middleware.proxy_fix.ProxyFix(app.wsgi_app, x_proto=1, x_host=1, x_prefix=1)
flask_babel.Babel(app, locale_selector=lambda: flask.request.accept_languages.best_match(["en", "cs"]))
app.register_blueprint(main.bp)

@app.template_filter('format_time')
def format_time(seconds):
  return str(datetime.timedelta(seconds=seconds))

@app.template_filter('format_size')
def format_size(size):
  for unit in ["B","KB","MB","GB"]:
    if abs(size) < 1024.0:
      return "%3.1f%s" % (size, unit)
    size /= 1024.0
