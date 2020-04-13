#!/usr/bin/python3

import copy
import os
import queue
import rpyc
import sched
import shutil
import string
import threading
import time
import uuid
import youtube_dl

service_timeout = 3600
download_timeout = 3600

class Remuxer(youtube_dl.postprocessor.ffmpeg.FFmpegPostProcessor):

  def __init__(self, downloader, out_directory, filepath_hook):
    super(Remuxer, self).__init__(downloader)
    self.out_directory = out_directory
    self.filepath_hook = filepath_hook

  def run(self, information):
    path = information["filepath"]
    prefix, sep, ext = path.rpartition(".")
    outpath = os.path.join(self.out_directory, prefix + sep + "mkv")
    options = ["-c:v", "copy", "-c:a", "copy"]
    self.run_ffmpeg(path, outpath, options)
    self.filepath_hook(outpath)
    information["filepath"] = outpath
    information["format"] = "mkv"
    information["ext"] = "mkv"
    return [path], information

class Scheduller:

  def __init__(self):
    self.running = True
    self.lock = threading.Lock()
    self.condition = threading.Condition(self.lock)
    self.scheduller = sched.scheduler(time.time, self.condition.wait)
    self.thread = threading.Thread(target = self.entry_point)
    self.thread.start()

  def entry_point(self):
    with self.lock:
      while self.running:
        self.condition.wait()
        self.scheduller.run()

  def enter(self, delay, priority, action, argument=()):
    with self.lock:
      event = self.scheduller.enter(delay, priority, action, argument)
      self.condition.notify()
      return event

  def cancel(self, event):
    with self.lock:
      if event in self.scheduller.queue:
        self.scheduller.cancel(event)
        self.condition.notify()
        return True
      return False

  def terminate(self, force = False):
    with self.lock:
      self.running = False
      if force:
        while self.scheduller.queue:
          event = self.scheduller.queue[0]
          self.scheduller.cancel(event)
      self.condition.notify()
    self.thread.join()

class Downloader:

  def __init__(self, scheduller):
    self.scheduller = scheduller
    self.running = True
    self.downloads = []
    self.request_queue = queue.Queue()
    self.status_lock = threading.Lock()
    self.worker_thread = threading.Thread(target = self.entry_point)
    self.worker_thread.start()

  def entry_point(self):
    while self.running:
      task = self.request_queue.get()
      if task:
        with self.status_lock:
          self.current_task = task
        task["active"] = True
        try:
          params = {"cachedir": False, "format": task["format"], "progress_hooks": [self.progress_hook], "ratelimit": 512 * 1024}
          with youtube_dl.YoutubeDL(params) as ydl:
            ydl.add_post_processor(Remuxer(ydl, task["directory"], self.filepath_hook))
            task["info"] = ydl.extract_info(task["address"])
          task["done"] = True
        except Exception as e:
          task["error"] = str(e)
          task["failed"] = True
        task["active"] = False
        for root, dirs, files in os.walk("."):
          if root == ".":
            for file in files:
              try:
                os.remove(os.path.join(root, file))
              except:
                pass
        self.scheduller.enter(download_timeout, 0, self.delete_task, (task, ))

  def progress_hook(self, progress):
    with self.status_lock:
      self.current_task["progress"] = progress
    if not self.running:
      raise Exception("Service is shutting down")

  def filepath_hook(self, filepath):
    with self.status_lock:
      self.current_task["filepath"] = filepath
      try:
        self.current_task["filesize"] = os.path.getsize(filepath)
      except:
        pass

  def delete_task(self, task):
    with self.status_lock:
      self.downloads.remove(task)
    try:
      shutil.rmtree(task["directory"])
    except:
      pass

  def metadata(self, address):
    try:
      params = {"cachedir": False}
      with youtube_dl.YoutubeDL(params) as ydl:
        return ydl.extract_info(address, download=False)
    except:
      return None

  def download(self, address, format):
    directory = str(uuid.uuid1())
    os.mkdir(directory)
    task = {"address": address, "format": format, "directory": directory}
    with self.status_lock:
      self.downloads.append(task)
    self.request_queue.put(task)
    return directory

  def get_downloads(self):
    with self.status_lock:
      return copy.deepcopy(self.downloads)

  def terminate(self):
    self.running = False
    self.request_queue.put(None)
    self.worker_thread.join()
    for root, dirs, files in os.walk("."):
      if root == ".":
        for dir in dirs:
          try:
            shutil.rmtree(os.path.join(root, dir))
          except:
            pass

class DownloadService(rpyc.Service):

  def __init__(self, server):
    self.server = server
    self.exiting = False

  def on_connect(self, conn):
    self.server.refresh()

  def on_disconnect(self, conn):
    if self.exiting:
      self.server.exit()

  def exposed_metadata(self, address):
    return self.server.downloader.metadata(address)

  def exposed_download(self, address, format):
    return self.server.downloader.download(address, format)

  def exposed_get_downloads(self):
    return self.server.downloader.get_downloads()

  def exposed_exit(self):
    self.exiting = True

class Server:

  def __init__(self):
    self.scheduller = Scheduller()
    self.downloader = Downloader(self.scheduller)
    self.service = rpyc.utils.helpers.classpartial(DownloadService, self)

  def __enter__(self):
    return self

  def __exit__(self, type, value, traceback):
    self.downloader.terminate()
    self.scheduller.terminate(True)

  def start(self):
    self.server = rpyc.utils.server.ThreadedServer(self.service, port = 18861)
    self.terminate = self.scheduller.enter(service_timeout, 0, self.server.close)
    self.server.start()

  def refresh(self):
    if self.scheduller.cancel(self.terminate):
      self.terminate = self.scheduller.enter(service_timeout, 0, self.server.close)

  def exit(self):
    if self.scheduller.cancel(self.terminate):
      self.terminate = self.scheduller.enter(0, 0, self.server.close)

def main():
  with Server() as server:
    server.start()

if __name__ == "__main__":
  main()
