import threading 
import time


# Scheduler exposes interfaces to initialize and start a scheduled cron job in a non-blocking thread
class Scheduler(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.next_call = time.time()

    def _run(self):
        self.is_running = False
        self._start()
        self.function(*self.args, **self.kwargs)

    def _start(self):
        if not self.is_running:
            self.next_call += self.interval
            self._timer = threading.Timer(self.next_call - time.time(), self._run)
            self._timer.start()
            self.is_running = True

    def start(self, initial_delay_in_secs=0):
        if not self.is_running:
            self.next_call += initial_delay_in_secs
            self._timer = threading.Timer(self.next_call - time.time(), self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False
