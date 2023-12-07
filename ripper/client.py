#!/usr/bin/python3

import os
import rpyc
import time

class Client:

  def __init__(self):
    self.connection = self.connect()

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.connection.close()
    self.connection = None

  def connect(self):
    for i in range(0, 5):
      try:
        return rpyc.connect("localhost", 18861)
      except ConnectionRefusedError:
        if i == 0:
          connection = rpyc.classic.connect("localhost")
          connection.modules.os.chdir(os.environ["FLASK_APP"])
          connection.modules.os.system("./service.py &")
        time.sleep(2)
    raise Exception("Unable to connect to the service")

  def metadata(self, address):
    return self.connection.root.metadata(address)

  def download(self, address, format = None):
    return self.connection.root.download(address, format)

  def get_downloads(self):
    return self.connection.root.get_downloads()

  def exit(self):
    self.connection.root.exit()
