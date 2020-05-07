import time
import logging

from ..base import BaseThread

logger = logging.getLogger(__name__)


class StepLoop(BaseThread):
    """A thread that runs in the background and runs a sequence of steps.
    """
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
