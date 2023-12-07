#!/usr/bin/python3

import copy
import os
import pathlib
import queue
import rpyc
import sched
import shutil
import string
import threading
import time
import uuid
import yt_dlp

service_timeout = 3600
download_timeout = 3600

class Remuxer(yt_dlp.postprocessor.ffmpeg.FFmpegPostProcessor):

  def __init__(self, downloader, filepath_hook):
    super(Remuxer, self).__init__(downloader)
    self.filepath_hook = filepath_hook

  def run(self, information):
    path = information["filepath"]
    outpath = str(pathlib.Path(path).with_suffix(".mkv"))
    options = ["-c:v", "copy", "-c:a", "copy"]
    self.run_ffmpeg(path, outpath, options)
    self.filepath_hook(outpath)
    information["filepath"] = outpath
    information["format"] = "mkv"
    information["ext"] = "mkv"
    return [path], information

class Scheduler:

  def __init__(self):
    self.running = True
    self.lock = threading.Lock()
    self.condition = threading.Condition(self.lock)
    self.scheduler = sched.scheduler(time.time, self.condition.wait)
    self.thread = threading.Thread(target = self.entry_point)
    self.thread.start()

  def entry_point(self):
    with self.lock:
      while self.running:
        self.condition.wait()
        self.scheduler.run()

  def enter(self, delay, priority, action, argument=()):
    with self.lock:
      event = self.scheduler.enter(delay, priority, action, argument)
      self.condition.notify()
      return event

  def cancel(self, event):
    with self.lock:
      if event in self.scheduler.queue:
        self.scheduler.cancel(event)
        self.condition.notify()
        return True
      return False

  def terminate(self, force = False):
    with self.lock:
      self.running = False
      if force:
        while self.scheduler.queue:
          event = self.scheduler.queue[0]
          self.scheduler.cancel(event)
      self.condition.notify()
    self.thread.join()

class Downloader:

  def __init__(self, scheduler):
    self.scheduler = scheduler
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
          params = {"cachedir": False, "format": task["format"], "paths": {"home": task["directory"]}, "progress_hooks": [self.progress_hook], "ratelimit": 512 * 1024}
          with yt_dlp.YoutubeDL(params) as ydl:
            ydl.add_post_processor(Remuxer(ydl, self.filepath_hook))
            task["info"] = ydl.extract_info(task["address"])
          task["done"] = True
        except Exception as e:
          task["error"] = str(e)
          task["failed"] = True
        task["active"] = False
        self.scheduler.enter(download_timeout, 0, self.delete_task, (task, ))

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
      with yt_dlp.YoutubeDL(params) as ydl:
        return ydl.extract_info(address, download=False)
    except:
      return None

  def download(self, address, format):
    directory = os.path.join("static", str(uuid.uuid1()))
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
    for root, dirs, files in os.walk("static"):
      for dir in dirs:
        try:
          shutil.rmtree(os.path.join(root, dir))
        except:
          pass
      dirs.clear()

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
    self.scheduler = Scheduler()
    self.downloader = Downloader(self.scheduler)
    self.service = rpyc.utils.helpers.classpartial(DownloadService, self)

  def __enter__(self):
    return self

  def __exit__(self, type, value, traceback):
    self.downloader.terminate()
    self.scheduler.terminate(True)

  def start(self):
    self.server = rpyc.utils.server.ThreadedServer(self.service, port = 18861)
    self.terminate = self.scheduler.enter(service_timeout, 0, self.server.close)
    self.server.start()

  def refresh(self):
    if self.scheduler.cancel(self.terminate):
      self.terminate = self.scheduler.enter(service_timeout, 0, self.server.close)

  def exit(self):
    if self.scheduler.cancel(self.terminate):
      self.terminate = self.scheduler.enter(0, 0, self.server.close)

def main():
  with Server() as server:
    server.start()

if __name__ == "__main__":
  main()
