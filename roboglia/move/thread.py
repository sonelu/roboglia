import time
import logging

from ..base import BaseThread, BaseLoop
from ..utils import check_not_empty

logger = logging.getLogger(__name__)


class StepLoop(BaseThread):
    """A thread that runs in the background and runs a sequence of steps.

    Parameters
    ----------
    name: str
        The name of the step loop.

    patience: float
        A duration in seconds that the main thread will wait for the
        background thread to finish setup activities and indicate that it
        is in ``started`` mode.

    times: int
        How many times the loop should be played. If a negative number is
        given (ex. -1) the loop will play to infinite
    """
    def __init__(self, name='STEPLOOP', patience=1.0, times=1):
        super().__init__(name=name, patience=patience)
        self.__times = times

    @property
    def times(self):
        return self.__times

    def play(self):
        """Provides the step data. Should be overridden by subclasses and
        implement a ``yield`` logic. :py:meth:`run` invokes ``next`` on this
        method to get the data and the duration needed to perform one step.
        """
        yield None, 0                   # pragma: no cover

    def setup(self):
        """Resets the loop from the begining."""
        pass

    def run(self):
        """Wraps the execution between the duration provided and
        decrements iteration run.
        """
        iteration = self.times
        while iteration != 0:
            for data, duration in self.play():
                logger.debug(f'data={data}, duration={duration}')
                # handle stop requests
                if self.stopped:
                    logger.debug('Thread stopped')
                    return None
                # handle pause requests
                while self.paused:
                    time.sleep(0.001)          # 1ms
                # process
                start_time = time.time()
                self.atomic(data)
                end_time = time.time()
                wait_time = duration - (end_time - start_time)
                if wait_time > 0:               # pragma: no branch
                    time.sleep(wait_time)
            iteration -= 1

    def atomic(self, data):
        """Executes the step.

        Must be overridden in subclass to perform the specific operation on
        data.
        """
        raise NotImplementedError


class Motion(BaseLoop):
    """Class that helps with the implementation of code-driven joint control.
    It is a subclass of :py:class:`BaseLoop` and inherits all its properties.
    In addition it stores references to the ``robot`` and the ``joints`` that
    are used. For convenience it includes a ``ticks`` property that provides
    the number of seconds from the start of the loop. It is intended to be
    used to generate behavior that is dependent of time (ex. sinus / cosines)
    trajectories.

    Parameters
    ----------

    name: str
        The name of the motion

    patience: float
        A duration in seconds that the main thread will wait for the
        background thread to finish setup activities and indicate that it
        is in ``started`` mode.

    frequency: float
        The loop frequency in [Hz]

    warning: float
        Indicates a threshold in range [0..1] indicating when
        warnings should be logged to the logger in case the execution
        frequency is bellow the target. A 0.8 value indicates the real
        execution is less than 0.8 * target_frequency. The statistic is
        calculated over a period of time specified by the parameter `review`.

    throttle: float
        Is a float (< 1.0) that is used by the monitoring of
        execution statistics to adjust the wait time in order to produce
        the desired processing frequency.

    review: float
        The time in [s] to calculate the statistics for the frequency.

    robot: JointManager or subclass
        The robot Joint Manager that controls the moves.

    joints: list of Joint or subclass
        The joints used by the motion process.
    """
    def __init__(self, name='MOTION', patience=1.0, frequency=None,
                 warning=0.90, throttle=0.1, review=1.0, manager=None,
                 joints=[]):
        super().__init__(name=name, patience=patience, frequency=frequency,
                         warning=warning, throttle=throttle, review=review)
        check_not_empty(manager, 'manager', 'motion', self.name, logger)
        self.__manager = manager
        check_not_empty(joints, 'joints', 'motion', self.name, logger)
        self.__joints = joints
        self.__ticks = time.time()

    def setup(self):
        """Called when starting the loop. Resets the ticks counter."""
        self.__ticks = time.time()

    def manager(self):
        """The robot associated with the motion."""
        return self.__manager

    def joints(self):
        """Joints used by the motion."""
        return self.__joints

    def ticks(self):
        """Seconds passed since the loop started."""
        return time.time() - self.__ticks

    def atomic(self):
        """Called with frequency ``frequency``, this should be implemented
        in the subclass that implements the motion."""
        raise NotImplementedError
