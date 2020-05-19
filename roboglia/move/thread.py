import time
import logging

from ..base import BaseThread

logger = logging.getLogger(__name__)


class StepLoop(BaseThread):
    """A thread that runs in the background and runs a sequence of steps.

    Parameters
    ----------
    name: str
        The name of the step loop

    times: int
        How many times the loop should be played. If a negative number is
        given (ex. -1) the loop will play to infinite
    """
    def __init__(self, name='STEPLOOP', times=1, **kwargs):
        super().__init__(name=name, **kwargs)
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
