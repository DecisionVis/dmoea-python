from collections import namedtuple
from random import random
from random import randint

from moeadv.Constants import MAXIMIZE
from moeadv.Constants import MINIMIZE

from moeadv.Constants import CENTERPOINT
from moeadv.Constants import OFAT
from moeadv.Constants import CORNERS
from moeadv.Constants import RANDOM
from moeadv.Constants import COUNT

from moeadv.Constants import RETAIN
from moeadv.Constants import DISCARD

from moeadv.Structures import Rank
from moeadv.Structures import Individual
from moeadv.Structures import ArchiveIndividual
from moeadv.Structures import DOEState
from moeadv.Structures import MOEAState

def _create_archive(problem, float_values, ranks, ranksize):
    # construct bogus individuals to fill the archive
    bogus_grid_position = tuple((999 for _ in problem.decisions))
    if float_values == RETAIN:
        bogus_decisions = tuple((0.0 for _ in problem.decisions))
    else:
        bogus_decisions = tuple()
    bogus_objectives = list()
    # in C, math.h has macros for infinity and nan
    inf = float("inf")
    ninf = -inf
    # Bogus individuals should never dominate true individuals.
    for objective in problem.objectives:
        if objective.sense == MAXIMIZE:
            bogus_objectives.append(ninf)
        else:
            bogus_objectives.append(inf)
    # Nor should they appear even remotely feasible.
    bogus_constraints = list()
    for constraint in problem.constraints:
        if constraint.sense == MAXIMIZE:
            bogus_constraints.append(ninf)
        else:
            bogus_constraints.append(inf)
    bogus_tagalongs = list((0.0 for _ in problem.tagalongs))
    bogus_archive_individual = ArchiveIndividual(
        bogus_grid_position,
        bogus_decisions,
        bogus_objectives,
        bogus_constraints,
        bogus_tagalongs)
    # Construct an archive full of references to the bogus individual
    archive = tuple((
        Rank([bogus_archive_individual for _ in range(ranksize)], 0)
        for _ in range(ranks)
    ))
    return archive

def create_moea_state(problem, **kwargs):
    """
    problem (Problem): definition of problem structure.

    keywords:
        ranks (int): number of ranks to allocate in the archive
                     (default 100)
        ranksize (int): number of individuals in a rank
                     (default 10,000)
        float_values (RETAIN or DISCARD): what to do with decision
                     variable values.  If RETAIN is selected,
                     the decision variable values will be stored
                     along with the grid points of every individual.
                     If there is a large number of decision variables,
                     this policy results in greatly increased storage
                     requirements, and may require a reduction in
                     ranks or ranksize for the archive to fit in
                     memory.  RETAIN may be a desirable behavior if
                     you are doing local optimization or providing
                     individuals that have been evaluated on a
                     different grid. 
                     If DISCARD is selected, the decision variable
                     values for each individual will not be stored
                     explicitly, and will be regenerated from the
                     individual's grid point.  As long as the
                     individuals provided to the algorithm were
                     evaluated at grid points in decision space, this
                     option is lossless and saves a lot of space.
                     DISCARD is the default for this option.
        random (callable): a real-number generating function,
                     returning a number on the interval [0,1).
                     If none is provided, we fall back on
                     Python's random.random.
        randint (callable): an integer generating function
                     taking two arguments, a lower bound and
                     an (inclusive) upper bound, and returning
                     a number within those bounds.  E.g.
                     calling intrand(0, 1) should return 0 or
                     1.  We expect this to be a random number
                     generator and the algorithm may not
                     converge if it is not.  If not provided,
                     we fall back on Python's random.randint.

    This function creates MOEA state, including
    pre-allocation of a large archive for individuals.

    If the individuals are very large, it may make sense
    to reduce ranks or ranksize to avoid an unnecessary
    allocation.  This entails a tradeoff: fewer ranks save
    memory but risk forgetting that a badly dominated
    point in decision space has already been sampled.
    Smaller ranksize can save a great deal of memory
    if selected appropriately, at the risk of degrading
    algorithmic performance when ranks overflow.
    """
    float_values = kwargs.get("float_values", DISCARD)
    ranks = kwargs.get('ranks', 100)
    ranksize = kwargs.get('ranksize', 10000)
    _random = kwargs.get('random', random)
    _randint = kwargs.get('randint', randint)
    archive = _create_archive(problem, float_values, ranks, ranksize)
    # initial DOE state is: do an OFAT DOE
    doestate = DOEState(CENTERPOINT, OFAT, 0, 0)

    state = MOEAState(
        problem,
        float_values,
        archive,
        _random,
        _randint,
        doestate
    )
    return state

def doe(state, **kwargs):
    """
    Return an MOEAState such that the next generated
    samples will begin to fill out a design of experiments
    on the decision space, rather than doing evolution
    on the archived individuals.  If this function is not
    called and initial evaluated samples are not provided,
    some DOE samples will still be generated until there
    is material for evolution.

    The DOE proceeds as:
        center point    (1 sample)
        OFAT            (2 * ndv samples)
        corners         (2 ^ ndv samples)
        random uniform  (unlimited samples)

    If a different DOE procedure works better for your problem,
    you may substitute one of your choosing by running the
    DOE separately and supplying evaluated individuals to
    the algorithm using return_evaluated_individual before
    beginning the evolution run.

    keywords:
        terminate (CENTERPOINT, OFAT, CORNERS, COUNT):
            indicates stage after which to switch from
            DOE to evolution. Defaults to OFAT, which
            means 2 * ndv + 1 samples will be generated
            before evolution starts.  If you have a lot
            of decision variables and choose CORNERS,
            you may never finish doing your DOE, but if
            you have a small number of decision variables
            it may be worth while.
            If you specify COUNT, then the number of DOE samples
            is determined by the "count" keyword argument.
        count (int): Number of DOE samples to perform, if COUNT
            is specified as a DOE termination condition.
            Default is 2 * ndv + 1.
    """
    terminate = kwargs.get("terminate", OFAT)
    if terminate == COUNT:
        default_count = 2 * len(state.problem.decisions) + 1
        count = kwargs.get("count", default_count)
    else:
        count = 0
    old_doestate = state.doestate
    new_doestate = old_doestate._replace(
        terminate=terminate,
        remaining=count)
    new_state = state._replace(doestate=new_doestate)
    return new_state

def return_evaluated_individual(state, individual):
    """
    Return an MOEAState that accounts for the returned
    individual.
    """

