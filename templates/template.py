from moeadv.moeadv import MOEA
from moeadv.moeadv import Decision
from moeadv.moeadv import Objective
from moeadv.moeadv import Constraint
from problems.problems import dtlz2
from problems.problems import dtlz2_rotated

evaluate = dtlz2_rotated(3, 2)

delta = 0.05

decisions = (
    Decision("x1", 0.0, 1.0, delta),
    Decision("x2", 0.0, 1.0, delta),
    Decision("x3", 0.0, 1.0, delta),
)

max_samples = delta ** -3

objectives = (
    Objective("y1", "min"),
    Objective("y2", "min"),
)

constraints = tuple()

moea = MOEA(decisions, objectives, constraints)
# Force the MOEA into the "DOE" state for an initial sampling
# run of 100 samples.
# It will transition to the "evolving" state automatically
# when the initial samples have been generated.
moea.doe(100)
for nfe in range(1, 10001):
    dvs = moea.generate_sample()
    objs = evaluate(dvs)
    moea.receive_evaluated_sample(dvs, objs)
    if len(moea.samples) >= max_samples: break
    print(moea.evolution_count())
    if moea.evolution_count() >= 500:
        print("doin' a restart!")
        # Replace population with archive and force the MOEA
        # into the "injecting" state, which produces new samples
        # from mutated archive solutions rather than by evolving
        # the population.  The MOEA will transition back to the
        # "evolving" state automatically and reset the evolution
        # counter when it does so.
        moea.inject(4.0)

print("{},{},{},{},{}".format(
    decisions[0].name,
    decisions[1].name,
    decisions[2].name,
    objectives[0].name,
    objectives[1].name))

for row in moea.archive_rows():
    print(",".join(("{}".format(x) for x in row)))

