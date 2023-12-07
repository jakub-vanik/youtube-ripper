#!/usr/bin/python3

import flask
import os

from . import babel
from . import main

class ReverseProxied:

  def __init__(self, app, script_name):
    self.app = app
    self.script_name = script_name

  def __call__(self, environ, start_response):
    if self.script_name:
      environ["SCRIPT_NAME"] = self.script_name
    scheme = environ.get("HTTP_X_FORWARDED_PROTO")
    if scheme:
      environ["wsgi.url_scheme"] = scheme
    return self.app(environ, start_response)

def create_app():
  app = flask.Flask(__name__)
  app.config["SECRET_KEY"] = b'\xcbwG\xc8.s\xbe\xf6\xaf`\xc3xL\xa2\x10s'
  app.config["SESSION_COOKIE_NAME"] = "ripper_session"
  app.config["SESSION_COOKIE_HTTPONLY"] = False
  babel.babel.init_app(app)
  app.register_blueprint(main.bp)
  app.wsgi_app = ReverseProxied(app.wsgi_app, os.environ.get("SCRIPT_NAME"))
  return app
