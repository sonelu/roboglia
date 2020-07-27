import yaml
import logging

# from ..utils import check_key
from .thread import StepLoop
from ..base import PVLList

logger = logging.getLogger(__name__)


class Script(StepLoop):
    """A Script is the top level structure used for defining prescribed
    motion for a robot.

    Parameters
    ----------
    name: str
        The name of the script

    patience: float
        A duration in seconds that the main thread will wait for the
        background thread to finish setup activities and indicate that it
        is in ``started`` mode.

    times: int
        How many times the loop should be played. If a negative number is
        given (ex. -1) the loop will play to infinite

    robot: BaseRobot or subclass
        The robot that will be performing the script

    defaults: dict
        A dictionary with default behavior. Supported elements for the
        moment:

        - "duration" (specifies the duration of a sequence transition,
          if no explicit one is provided)
        - others to come...

    times: int
        The number of times the script steps will be executed when
        :py:meth:`play` will be invoked. Default is 1.

    joints: list of Joint or subclasses
        An ordered list of joints that are used by the script. The ``frame``
        definitions later uses this order when describing the states.

    frames: dict of :py:class:`Frame`
        The Frame definitions used by the script. See the information for
        this class for more details.

    sequences: dict of :py:class:`Sequence`
        The Sequence defintions that are used by the script. See the
        information for this class for more details.

    scenes: dict of :py:class:`Scene`
        The Scene defintions used by the Script. See the information for this
        class for more details.

    script: list of :py:class:`Scene`
        An ordered list of Scenes that represent the complete Script. When
        the script is played the scenes are run in the order provided and,
        if the ``times`` parameter is different than 1, it will repeat the
        execution in a loop.
    """
    def __init__(self, name='SCRIPT', patience=1.0, times=1,
                 robot=None, defaults={},
                 joints=[], frames={}, sequences={}, scenes={}, script=[]):
        super().__init__(name=name, patience=patience, times=times)
        self.__robot = robot
        self.__defaults = defaults
        self.__init_joints(joints)
        self.__init_frames(frames)
        self.__init_sequences(sequences)
        self.__init_scenes(scenes)
        self.__init_script(script)

    @classmethod
    def from_yaml(cls, robot, file_name):
        """Reads the script defintion from a YAML file."""
        with open(file_name, 'r') as f:
            init_dict = yaml.load(f, Loader=yaml.FullLoader)
        if len(init_dict) > 1:              # pragma: no branch
            logger.warning('only the first script will be loaded')
        name = list(init_dict)[0]
        components = init_dict[name]
        return cls(name=name, robot=robot, **components)

    def __init_joints(self, joints):
        """Used by __init__ to setup the joints. Incorrect joints will be
        marked with ``None`` and will be filtered out when commands are
        issued.
        """
        for index, joint_name in enumerate(joints):
            rm_joints = [joint.name for joint in self.robot.manager.joints]
            if joint_name not in rm_joints:
                logger.warning(f'Joint {joint_name} used in script {self.name}'
                               ' is not managed by the robot manager '
                               f'{self.robot.manager.name} '
                               'and will be skipped')
                joints[index] = None
            else:
                joints[index] = self.robot.joints[joint_name]
        self.__joints = joints

    def __init_frames(self, frames):
        """Used by __init__ to setup the frames. Handles full frames (dict
        of position, velocity and loads) or simplified frames (list of
        positions only)."""
        self.__frames = {}
        for frame_name, frame_info in frames.items():
            if isinstance(frame_info, list):
                new_frame = Frame(name=frame_name, positions=frame_info)
            elif isinstance(frame_info, dict):
                new_frame = Frame(name=frame_name, **frame_info)
            else:
                raise NotImplementedError
            self.__frames[frame_name] = new_frame

    def __init_sequences(self, sequences):
        """Used by __init__ to setup the sequences. Frames incorrectly
        referenced will the skipped."""
        self.__sequences = {}
        for seq_name, seq_info in sequences.items():
            frames = seq_info.get('frames', [])
            if not frames:
                logger.warning(f'sequence {seq_name} has no frames defined')
                self.__sequences[seq_name] = None
            else:
                # check the frame names and replace with objects
                for index, frame_name in enumerate(frames):
                    if frame_name not in self.frames:
                        logger.warning(f'frame {frame_name} used by sequence '
                                       f'{seq_name} does not exits '
                                       'and will be skipped')
                        frames[index] = None
                    else:
                        frames[index] = self.frames[frame_name]

                self.__sequences[seq_name] = \
                    Sequence(name=seq_name, **seq_info)

    def __init_scenes(self, scenes):
        """Used by __init__ to setup scenes."""
        self.__scenes = {}
        for scene_name, scene_info in scenes.items():
            sequences = scene_info.get('sequences', None)
            if not sequences:
                logger.warning(f'Scene "{scene_name}" does not have any '
                               f'sequences defined; will skip')
                self.__scenes[scene_name] = None
            else:
                # replace sequence names with object references
                for index, seq_name in enumerate(sequences):
                    # for a scene the sequence representation will be a dict
                    # that includes the sequence reference and the direction
                    # of play (inverse)
                    seq = {}
                    # check for inverse request
                    if '.reverse' in seq_name:
                        seq['reverse'] = True
                        seq_name = seq_name.replace('.reverse', '')
                    else:
                        seq['reverse'] = False
                    # validate the sequence exists
                    # if not log error and use None
                    if seq_name not in self.sequences:
                        logger.warning(f'Sequence "{seq_name}" used by scene '
                                       f'"{scene_name}" does not exist; '
                                       'will skip')
                        seq['sequence'] = None
                    else:
                        seq['sequence'] = self.sequences[seq_name]
                    # now replace the sequence name with the enhanced reference
                    sequences[index] = seq
                # update the scenes dictionary
                self.__scenes[scene_name] = \
                    Scene(name=scene_name, **scene_info)

    def __init_script(self, script):
        """Called by __init__ to setup the script steps."""
        for index, scene_name in enumerate(script):
            if scene_name not in self.scenes:
                logger.warning(f'Scene "{scene_name}" used by script '
                               f'"{self.name}" does not exist; will skip')
                script[index] = None
            else:
                script[index] = self.scenes[scene_name]
        self.__script = script

    @property
    def robot(self):
        """The robot associated with the Script."""
        return self.__robot

    @property
    def defaults(self):
        """Default values for Script."""
        return self.__defaults

    @property
    def joints(self):
        """The joints used by the Script."""
        return self.__joints

    @property
    def frames(self):
        """The dictionary of Frames used by the Script."""
        return self.__frames

    @property
    def sequences(self):
        """The dictionary of Sequences used by the Script."""
        return self.__sequences

    @property
    def scenes(self):
        """The dictionary of Scenes used by the Script."""
        return self.__scenes

    @property
    def script(self):
        """Returns the script (the list of scenes to be executed)."""
        return self.__script

    def play(self):
        """Inherited from :py:class:`StepLoop`. Iterates over the scenes
        and produces the commands."""
        logger.debug(f'Script {self.name} playing')
        for scene in self.script:
            if scene:           # pragma: no branch
                logger.debug(f'Script {self.name} playing scene {scene.name}')
                for frame, duration in scene.play():
                    yield frame, duration

    def atomic(self, data):
        """Inherited from :py:class:`StepLoop`. Submits the data to the
        robot manager only for valid joints."""
        # data is a list of tuples with the commands for each joint
        assert len(data) == len(self.joints)
        # because self.joints could contain None values we cannot use zip
        commands = {}
        for index, joint in enumerate(self.joints):
            if joint:
                commands[joint.name] = data[index]
        logger.debug(f'Submitting: {commands}')
        self.robot.manager.submit(self, commands)

    def teardown(self):
        """Informs the robot manager we are finished."""
        for _ in range(5):
            if self.robot.manager.stop_submit(self):
                logger.info(f'Script {self.name} successfully unsubscribed')
                return None
        logger.warning(f'Script {self.name} failed to unsubscribe from '
                       'Joint Manager')


class Scene():
    """A Scene is a collection of :py:class:`Sequence` presented in an ordered
    list.

    Parameters
    ----------
    name: str
        The name of the Scene

    sequences: list of :py:class:`Sequence`
        The Sequences that make the Scene.

    times: int
        A repeat counter for playing the list of Sequences when the
        :py:meth:`play` is invoked.
    """
    def __init__(self, name='SCENE', sequences=[], times=1):
        self.__name = name
        self.__sequences = sequences
        self.__times = times

    @property
    def name(self):
        """The name of the Scene."""
        return self.__name

    @property
    def sequences(self):
        """The list of Sequences in the Scene."""
        return self.__sequences

    @property
    def times(self):
        """The repetition counter for the Scene."""
        return self.__times

    def play(self):
        """Performs a Scene. Inherited from :py:class:`StepLoop`. Iterates
        over the Sequences and produces the commands."""
        for step in range(self.times):
            logger.debug(f'Scene "{self.name}" playing iteration {step+1}')
            for seq_ext in self.sequences:
                sequence = seq_ext['sequence']
                reverse = seq_ext['reverse']
                rev_text = ' in reverse' if reverse else ''
                if not sequence:
                    logger.debug(f'Scene "{self.name}" playing sequence '
                                 '<None> sequence - skipping')
                else:
                    logger.debug(f'Scene "{self.name}" playing sequence '
                                 f'"{sequence.name}"{rev_text}')
                    for frame, duration in sequence.play(reverse=reverse):
                        yield frame, duration


class Sequence():
    """A Sequence is an ordered list of of frames that have associated
    durations in seconds and can be played in a loop a number of times.

    Parameters
    ----------
    name: str
        The name of the sequence

    frames: list of :py:class:`Frame`
        The frames contained in the sequence. The order in which the frames
        are listed is the order in which they will be played

    durations: list of float
        The durations in seconds for each frame. If the length of the list
        is different than the length of the frames there will be a
        critical error logged and the sequence will not be loaded.

    times: int
        The number of times the sequence should be played. Default is 1.
    """
    def __init__(self, name='SEQUENCE', frames=[], durations=[], times=1):
        self.__name = name
        if len(frames) != len(durations):
            logger.warning(f'Durations for sequence "{name}" different than '
                           'the number of frames; will skip')
            return None
        # normal processing
        self.__frames = frames
        self.__durations = durations
        self.__times = times

    @property
    def name(self):
        """The name of the sequence."""
        return self.__name

    @property
    def frames(self):
        """The list of ``Frame`` in the sequence."""
        return self.__frames

    @property
    def durations(self):
        """The durations associated with each frame."""
        return self.__durations

    @property
    def times(self):
        """The number of times the sequence will be played in a loop."""
        return self.__times

    def play(self, reverse=False):
        """Plays the sequence. Produces an iterator over all the frames,
        repeating as many ``times`` as requested.

        Parameters
        ----------
        reverse: bool
            Indicates if the frames should be played in reverse order.

        Returns
        -------
        iterator of tuple (commands, duration)
            ``commands`` is the list of (pos, vel, load) for each joint
            from the frame, and ``duration`` is the specified duration for
            the frame.
        """
        for step in range(self.times):
            logger.debug(f'Sequence "{self.name}" playing iteration {step+1}')
            if reverse:
                zipped = zip(reversed(self.frames), reversed(self.durations))
            else:
                zipped = zip(self.frames, self.durations)
            for frame, duration in zipped:
                if frame:
                    logger.debug(f'Sequence "{self.name}" playing frame '
                                 f'"{frame.name}", duration {duration}')
                    yield frame.commands, duration
                else:
                    logger.debug(f'Sequence "{self.name}" playing frame '
                                 '<None> frame - skipping')


class Frame():
    """A ``Frame`` is a single representation of the robots' joints at one
    point in time. It is described by a list of positions, the velocities
    wanted to get to those positions and the loads. The last two of them
    are optional and will be padded with ``nan`` in case they do not cover
    all positions listed in the first parameter.

    Parameters
    ----------
    name: str
        The name of the frame

    positions: list of floats
        The desired positions for the joints. They are provided in the same
        order as the number of joints that are described at the begining
        of the :py:class:`Script` where the frame is used. The unit of
        measure is the one used for the joints which in turn is dependent
        on the settings of the registers used by joints.

    velocities: list of floats
        The velocities used to move to the desired positions. If they are
        empty or not all covered, the constructor will padded with ``nan``
        to make it the same size as the positions. You can also use ``nan``
        in the list to indicate that a particular joint does not need to
        change the velocity (will continue to use the one set previously).

    loads: list of floats
        The loads used to move to the desired positions. If they are
        empty or not all covered, the constructor will padded with ``nan``
        to make it the same size as the positions. You can also use ``nan``
        in the list to indicate that a particular joint does not need to
        change the load (will continue to use the one set previously).
    """
    def __init__(self, name='FRAME', positions=[], velocities=[], loads=[]):
        self.__name = name
        self.__pvl = PVLList(positions, velocities, loads)

    @property
    def name(self):
        return self.__name

    @property
    def positions(self):
        """Returns the positions of a frame."""
        return self.__pvl.positions

    @property
    def velocities(self):
        """Returns the (padded) velocities of a frame."""
        return self.__pvl.velocities

    @property
    def loads(self):
        """Returns the (padded) loads of a frame."""
        return self.__pvl.loads

    @property
    def commands(self):
        """Returns a list of tuples (pos, vel, load) for each joint in the
        frame.
        """
        return self.__pvl
