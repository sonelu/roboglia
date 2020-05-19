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

from ..utils import check_type, check_not_empty

logger = logging.getLogger(__name__)


class BaseThread():
    """Implements a class that wraps a processing logic that is executed
    in a separate thread with the ability to pause / resume or fully stop
    the task.


    The main processing should be implemented in the `run` method where the
    subclass should make sure that it checks periodically the status
    (`paused` or `stopped`) and behave appropriately. The `run` can
    be flanked by the `setup` and `teardown` methods where subclasses can
    implement logic needed before the main processing is started or finished.

    This becomes very handy for loops that normally prepare the work, then
    run for an indefinite time, and later are closed when the owner signals.

    Parameters
    ----------
    name: str
        The name of the thread.

    patience: float
        A duration in seconds that the main thread will wait for the
        background thread to finish setup activities and indicate that it
        is in ``started`` mode.
    """
    def __init__(self, name='THREAD', patience=1.0, **kwargs):
        # name should have been checked by the robot
        self.__name = name
        check_not_empty(patience, 'patience', 'thread', self.name, logger)
        check_type(patience, float, 'thread', self.name, logger)
        self.__patience = patience
        self.__started = threading.Event()
        self.__paused = threading.Event()
        self.__crashed = False
        self.__thread = None

    @property
    def name(self):
        """Returns the name of the thread."""
        return self.__name

    def setup(self):
        """Thread preparation before running. Subclasses should override"""
        pass

    def run(self):
        """ Run method of the thread.

        .. note: In order to be stoppable (resp. pausable), this method has
            to check the running property - as often as possible to improve
            responsiveness - and terminate when :meth:`should_stop` (resp.
            :py:meth:`should_pause`) becomes True.

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
        pass

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
        """Wraps the execution of the task between the setup() and
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
        self.__thread.name = self.name
        self.__thread.start()

        if wait and (threading.current_thread() != self.__thread):
            if not self.__started.wait(self.__patience):
                if self.__crashed:
                    mess = f'Setup failed, for {self.__thread.name}.'
                else:
                    mess = f'Setup took longer than {self.__patience}s ' + \
                           f'for {self.__thread.name}'
                self.__thread.join()
                logger.critical(mess)
                raise RuntimeError(mess)

    def stop(self, wait=True):
        """Sends the stopping signal to the thread. By default waits for
        the thread to finish."""
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

    Parameters
    ----------
    name: str
        The name of the loop

    frequency: float
        The loop frequency in [Hz]

    warning: float
        Indicates a threshold in range [0..1] indicating when
        warnings should be logged to the logger in case the execution
        frequency is bellow the target. A 0.8 value indicates the real
        execution is less than 0.8 * target_frequency. The statistic is
        calculated over a period of time specified by the parameter `review`.

    throttle: float
        Is a float (small) that is used by the monitoring of
        execution statistics to adjust the wait time in order to produce
        the desired processing frequency.


    review: float
        The time in [s] to calculate the statistics for the frequency.

    Raises
    ------
        KeyError and ValueError if provided data in the initialization
        dictionary are incorrect or missing.
    """
    def __init__(self, frequency=None, warning=0.90,
                 throttle=0.02, review=1.0, **kwargs):
        super().__init__(**kwargs)
        check_not_empty(frequency, 'frequency', 'loop', self.name, logger)
        check_type(frequency, float, 'loop', self.name, logger)
        self.__frequency = frequency
        self.__period = 1.0 / self.__frequency
        check_not_empty(warning, 'warning', 'loop', self.name, logger)
        check_type(warning, float, 'loop', self.name, logger)
        self.__warning = warning
        check_not_empty(throttle, 'throttle', 'loop', self.name, logger)
        check_type(throttle, float, 'loop', self.name, logger)
        self.__throttle = throttle
        check_not_empty(review, 'review', 'loop', self.name, logger)
        check_type(review, float, 'loop', self.name, logger)
        self.__review = review
        # to keep statistics
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

    @property
    def warning(self):
        """Control the warning level for the warning message, the **setter**
        is smart: if the value is larger than 2 it will assume it is a
        percentage and divied it by 100 and ignore if the number is higher
        than 110.
        The over 100 is available for testing purposes.
        """
        return self.__warning

    @property
    def review(self):
        """Indicates the amount of time in seconds before the thread will
        review the actual frequency against the target and take action."""
        return self.__review

    @warning.setter
    def warning(self, value):
        if value < 2.0:
            self.__warning = value
        elif value <= 110:
            self.__warning = value / 100.0

    def run(self):
        exec_counts = 0
        last_count_reset = time.time()
        factor = 1.0            # fine adjust the rate
        while not self.stopped:
            if self.paused:
                # paused; reset the statistics
                exec_counts = 0
                last_count_reset = time.time()
                time.sleep(self.period)
            else:
                start_time = time.time()
                self.atomic()
                end_time = time.time()
                wait_time = self.__period - (end_time - start_time)
                wait_time *= factor
                if wait_time > 0:
                    time.sleep(wait_time)
                # statistics:
                exec_counts += 1
                if exec_counts >= self.__frequency * self.__review:
                    exec_time = time.time() - last_count_reset
                    actual_freq = exec_counts / exec_time
                    # fine tune the frequency
                    if actual_freq < self.__frequency:
                        # will reduce wait time
                        factor *= (1 - self.__throttle)
                    else:
                        # will increase wait time
                        factor *= (1 + self.__throttle)
                    if actual_freq < (self.__frequency * self.__warning):
                        logger.warning(
                            f'loop {self.name} running under '
                            f'warning threshold {actual_freq:.2f}[Hz] '
                            f'({actual_freq/self.__frequency*100:.0f}%')
                    # reset counters
                    exec_counts = 0
                    last_count_reset = time.time()

    def atomic(self):
        """This method implements the periodic task that needs to be
        executed. It does not need to check `paused` or `stopped` as the
        `run` method does this already and the subclasses should make sure
        that the implementation completes quickly and does not raise any
        exceptions.
        """
        raise NotImplementedError
