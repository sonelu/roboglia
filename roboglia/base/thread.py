# Copyright (C) 2020  Alex Sonea

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import threading
import time
import logging

from ..utils import check_key, check_type

logger = logging.getLogger(__name__)


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
        # name shoukld have been checkd by the robot
        self.__name = init_dict['name']
        self.__started = threading.Event()
        self.__paused = threading.Event()
        self.__crashed = False
        self.__thread = None

    @property
    def name(self):
        """Returns the name of the loop."""
        return self.__name

    def setup(self):
        """Thread preparation before running. Subclasses should override"""
        raise NotImplementedError

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
        raise NotImplementedError

    def teardown(self):
        """Thread cleanup. Subclasses should override."""
        raise NotImplementedError

    @property
    def started(self):
        """Indicates if the thread was started."""
        return self.__started.is_set()

    @property
    def stopped(self):
        """Indicates if the thread was stopped."""
        return not self.__started.is_set()

    @property
    def running(self):
        """Indicates if the thread is running."""
        return self.__started.is_set() and not self.__paused.is_set()

    @property
    def paused(self):
        """Indicates the thread was paused."""
        return self.__started.is_set() and self.__paused.is_set()

    def _wrapped_target(self):
        """Wrapps the execution of the task between the setup() and
        teardown() and sets / resets the events."""
        try:
            self.setup()
            self.__started.set()
            self.__paused.clear()
            self.run()
            self.__started.clear()
            self.teardown()
        except Exception:
            self.__crashed = True
            self.__started.clear()
            self.__paused.clear()
            raise

    def start(self, wait=True):
        """Starts the task in it's own thread."""
        if self.running:
            self.stop()
        self.__thread = threading.Thread(target=self._wrapped_target)
        self.__thread.daemon = True
        self.__thread.start()

        if wait and (threading.current_thread() != self.__thread):
            self.__started.wait()
            if self.__crashed:
                self.__thread.join()
                mess = f'Setup failed, see {self.__thread.name} for details.'
                logger.critical(mess)
                raise RuntimeError(mess)

    def stop(self, wait=True):
        """Sends the stopping signal to the thread. By default waits for
        the thred to finish."""
        if self.started:
            self.__started.clear()
            self.__paused.clear()
            if wait and (threading.current_thread() != self.__thread):
                while self.__thread.is_alive():
                    self.__started.clear()
                    self.__thread.join(timeout=1.0)

    def pause(self):
        """Requests the thread to pause."""
        if self.running:
            self.__paused.set()

    def resume(self):
        """Requests the thread to resume."""
        if self.paused:
            self.__paused.clear()


class BaseLoop(BaseThread):
    """This is a thread that executes in a separate thread, scheduling
    a certain atomic work (encapsulated in the `atomic` method) periodically
    as prescribed by the `frequency` parameter. The `run` method takes care
    of checking the flags for `paused` and `stopped` so there is no need
    to do this in the `atomic` method.

    Args:
        init_dict (dict): The dictionary used to initialize the loop.

    In addition to the keys required by the class :py:class:`BaseThread`
    the following keys are expected in the dictionary:

    - ``frequency``: the loop frequency in [Hz]

    The following keys are optional and can be omitted. They will be
    defaulted with the values mentioned bellow:

    - ``warning``: indicates a threshold in range [0..1] indicating when
      warnings should be logged to the logger in case the execution
      frequency is bellow the target. A 0.8 value indicates the real
      execution is less than 0.8 * taget_frequency. The statistic is
      calculated over a number of runs equal to the frequency (ex. if
      the frequency is 10 Hz the statistics will be claculated after
      10 execution cycles and then reset). If not provided the
      value 0.9 (90%) will be used.

    Raises:
        KeyError and ValueError if provided data in the initialization
        dictionary are incorrect or missing.
    """
    def __init__(self, init_dict):
        super().__init__(init_dict)
        check_key('frequency', init_dict, 'loop', self.name, logger)
        self.__frequency = init_dict['frequency']
        check_type(self.frequency, float, 'loop', self.name, logger)
        self.__period = 1.0 / self.frequency
        self.__warning = init_dict.get('warning', 0.90)
        # to keeep statistics
        self.__exec_counts = 0
        self.__last_count_reset = None

    @property
    def frequency(self):
        """Loop frequency."""
        return self.__frequency

    @property
    def period(self):
        """Loop period = 1 / frequency."""
        return self.__period

    def start(self):
        """Resets the statistics then calls the inherited ``start()``."""
        self.__exec_counts = 0
        self.__last_count_reset = time.time()
        super().start()

    def run(self):
        while not self.stopped:
            if not self.paused:
                start_time = time.time()
                self.atomic()
                end_time = time.time()
                wait_time = self.__period - (end_time - start_time)
                if wait_time > 0:
                    time.sleep(wait_time)
                # statistics:
                self.__exec_counts += 1
                if self.__exec_counts == self.__frequency:
                    exec_time = time.time() - self.__last_count_reset
                    actual_frequency = self.__exec_counts / exec_time
                    if actual_frequency < self.__frequency * self.__warning:
                        logger.warning(
                            f'loop {self.name} running under '
                            f'warning threshold {actual_frequency:.2f}[Hz] '
                            f'({actual_frequency/self.__frequency*100:.0f}%')
                    # reset counters
                    self.__exec_counts = 0
                    self.__last_count_reset = time.time()
            else:
                time.sleep(self.period)

    def atomic(self):
        """This method implements the periodic task that needs to be
        executed. It does not need to check `paused` or `stopped` as the
        `run` method does this already and the subclasses should make sure
        that the implementation completes quickly and does not raise any
        exceptions.
        """
        raise NotImplementedError


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
                time.sleep(0.001)          # 1ms

    def atomic(self):
        """Executes the step.

        Retrieves the execution method and the parameters from the steps
        dictionary.
        """
        method = getattr(self, self.steps[self.index]['execute'])
        params = self.steps[self.index]['parameters']
        method(params)
