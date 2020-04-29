import threading
import time


class BaseThread():
    """Implements a class that wraps a processing logic that is executed
    in a separate thread with the ability to pause / resume or fully stop
    the task.

    The main processing should be impemented in the `run` method where the
    subclass should make sure that it checks periodically the status
    (`paused` or `stopped`) and behave appropriately. The `run` can 
    be flanked by the `setup` and `teardown` mthods where subclasses can 
    impement logic needed before the main processing is started or finished.
    This becomes very handy for loops that normally prepare the work, then
    run for an indefinite time, and later are closed when the owner signals.
    """
    def __init__(self, init_dict):
        self.name = init_dict['name']

        self._started = threading.Event()
        self._paused = threading.Event()
        self._crashed = False
        self._thread = None


    def setup(self):
        """Thread preparation before running. Subclasses should override"""
        pass


    def run(self):
        """ Run method of the thread.
        .. note:: In order to be stoppable (resp. pausable), this method has to 
        check the running property - as often as possible to improve 
        responsivness - and terminate when :meth:`should_stop` (resp. 
        :meth:`should_pause`) becomes True.
            For instance::
                while <some condition for work>:
                    if not self.paused:
                        do_atom_work()
                    if self.stopped:
                        break
                    ...
        """
        pass


    def teardown(self):
        """Thread cleanup. Subclasses should override."""
        pass


    @property
    def started(self):
        """Indicates if the thread was started."""
        return self._started.is_set()


    @property
    def stopped(self):
        """Indicates if the thread was stopped."""
        return not self._started.is_set()


    @property
    def running(self):
        """Indicates if the thread is running."""
        return self._started.is_set() and not self._paused.is_set()

    
    @property
    def paused(self):
        """Indicates the thread was paused."""
        return self._started.is_set() and self._paused.is_set()


    def _wrapped_target(self):
        """Wrapps the execution of the task between the setup() and 
        teardown() and sets / resets the events."""
        try:
            self.setup()
            self._started.set()
            self._paused.clear()
            self.run()
            self._started.clear()
            self.teardown()
        except Exception:
            self._crashed = True
            self._started.clear()
            self._paused.clear()
            raise


    def start(self, wait=True):
        """Starts the task in it's own thread."""
        if self.running:
            self.stop()
        self._thread = threading.Thread(target=self._wrapped_target)
        self._thread.daemon = True
        self._thread.start()

        if wait and (threading.current_thread() != self._thread):
            self._started.wait()
            if self._crashed:
                self._thread.join()
                raise RuntimeError(f'Setup failed, see {self._thread.name} for details.')


    def stop(self, wait=True):
        """Sends the stopping signal to the thread. By default waits for
        the thred to finish."""
        if self.started:
            self._started.clear()
            self._paused.clear()
            if wait and (threading.current_thread() != self._thread):
                while self._thread.is_alive():
                    self._started.clear()
                    self._thread.join(timeout=1.0)

    def pause(self):
        """Requests the thread to pause."""
        if self.running:
            self._paused.set()


    def resume(self):
        """Requests the thread to resume."""
        if self.paused:
            self._paused.clear()




class BaseLoop(BaseThread):
    """This is a thread that executes in a separate thread, scheduling
    a certain atomic work (encapsulated in the `atomic` method) periodically
    as prescribed by the `frequency` parameter. The `run` method takes care
    of checking the flags for `paused` and `stopped` so there is no need
    to do this in the `atomic` method.
    """
    def __init__(self, init_dict):
        super().__init__(init_dict)
        self.frequency = init_dict['frequency']
        self.period  = 1.0 / self.frequency


    def run(self):
        while not self.stopped:
            if not self.paused:
                start_time = time.time()
                self.atomic()
                end_time = time.time()
                wait_time = self.period - (end_time - start_time)
                if wait_time > 0:
                    time.sleep(wait_time)
            else:
                time.sleep(self.period)


    def atomic(self):
        """This method implements the periodic task that needs to be
        executed. It does not need to check `paused` or `stopped` as the
        `run` method does this already and the subclasses should make sure
        that the implementation completes quickly and does not raise any
        exceptions.
        """
        pass


class StepLoop(BaseThread):

    def __init__(self, init_dict):
        super().__init__(init_dict)
        self.steps = init_dict['steps']
        self.loop = init_dict.get('loop', False)
        self.index = 0


    def setup(self):
        """Resets the loop from the begining."""
        self.index = 0


    def run(self):
        """Wraps the execution between the duration provided and
        increments index.
        """
        while not self.stopped:
            if not self.paused:
                start_time = time.time()
                self.atomic()
                end_time = time.time()
                step_duration = self.steps[self.index]['duration']
                wait_time = step_duration - (end_time - start_time)
                if wait_time > 0:
                    time.sleep(wait_time)
                self.index += 1
                if self.index == len(self.steps):
                    if self.loop:
                        self.index = 0
                    else:
                        break
            else:
                time.sleep(0.001) # 1ms


    def atomic(self):
        """Executes the step.

        Retrieves the execution method and the parameters from the steps 
        dictionary.
        """ 
        method = getattr(self, self.steps[self.index]['execute'])
        params = self.steps[self.index]['parameters']
        method(params)