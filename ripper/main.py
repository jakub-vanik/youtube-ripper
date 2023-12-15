#!/usr/bin/python3

import flask

from . import client
from . import session

bp = flask.Blueprint("main", __name__)

@bp.route("/", methods=["GET", "POST"])
def index():
  with client.Client() as flask.g.client:
    context = {}
    if flask.request.method == "POST":
      address = flask.request.form["address"]
      context["address"] = address
      context["meta"] = flask.g.client.metadata(address)
    return flask.render_template("index.html", **context)

@bp.route("/status")
def status():
  with client.Client() as flask.g.client, session.Session() as flask.g.session:
    downloads = flask.g.client.get_downloads()
    required_directories = flask.g.session.get_directories()
    existing_directories = set()
    for download in downloads:
      if download["directory"] in required_directories:
        existing_directories.add(download["directory"])
        download["hidden"] = False
      else:
        download["hidden"] = True
    flask.g.session.set_directories(existing_directories)
    context = {"downloads": downloads}
    return flask.render_template("status.html", **context)

@bp.route("/download", methods=["POST"])
def download():
  with client.Client() as flask.g.client, session.Session() as flask.g.session:
    address = flask.request.form["address"]
    video_format = flask.request.form["video_format"]
    audio_format = flask.request.form["audio_format"]
    format = video_format + "+" + audio_format
    format = format.strip("+")
    if not format:
      format = None
    directory = flask.g.client.download(address, format)
    flask.g.session.get_directories().add(directory)
    return flask.redirect(flask.url_for(".index"))

@bp.route("/restart", methods=["POST"])
def restart():
  with client.Client() as flask.g.client:
    flask.g.client.exit()
    return flask.redirect(flask.url_for(".index"))
