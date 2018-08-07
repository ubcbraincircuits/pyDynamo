import attr

from util import SAVE_META

@attr.s
class MotilityOptions():
    filoDist = attr.ib(default=5, metadata=SAVE_META)
    """ How short (in microns) branch needs to be to be considered a filopodia. """

    terminalDist = attr.ib(default=5, metadata=SAVE_META)
    """ Distance (in microns) between the final branch point and end of branch to be considered a filopodia. """

    excludeAxon = attr.ib(default=True, metadata=SAVE_META)
    """ Whether to exclude branches with points with 'axon' in their annotation. """

    excludeBasal = attr.ib(default=True, metadata=SAVE_META)
    """ Whether to exclude branches with points with 'basal' in their annotation. """

    includeAS = attr.ib(default=False, metadata=SAVE_META)
    """ Whether branch additions & subtractions are shown in motility plots. """

@attr.s
class ProjectOptions():
    pixelSizes = attr.ib(default=attr.Factory(lambda: [0.3070, 0.3070, 1.5]), cmp=False, metadata=SAVE_META)
    """ x/y/z size of each pixel in microns. """

    motilityOptions = attr.ib(default=attr.Factory(MotilityOptions), metadata=SAVE_META)
    """ What options to use when calculating and displaying motility details. """
