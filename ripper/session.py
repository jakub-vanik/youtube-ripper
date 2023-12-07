#!/usr/bin/python3

import flask

class Session:

  def __init__(self):
    if "directories" in flask.session:
      self.directories = set(flask.session["directories"])
    else:
      self.directories = set()

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    flask.session["directories"] = list(self.directories)

  def get_directories(self):
    return self.directories

  def set_directories(self, directories):
    self.directories = directories
