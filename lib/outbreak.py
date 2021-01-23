import pandas as pd
import numpy as np
import logging
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 unused import
plt.rcParams["figure.figsize"] = [12, 5]

from population.covid import PersonCovid
from population.population import FixedNetworkPopulation

from disease import covid_hazard


class Outbreak:
    def __init__(self, society, disease, pop_size=0, seed_size=0, n_days=0,
                 population=None,
                 population_type=None,
                 person_type=None):

        self.pop = self.prepare_population(pop_size, population, population_type, society, person_type)
        society.clear_queues()
        self.pop.seed_infections(seed_size, disease)

        self.initialize_timers(n_days, society.episodes_per_day)
        self.group_size = society.encounter_size

        self.society = society
        self.disease = disease

        self.set_recorder()

    def prepare_population(self, pop_size, population, population_type, society, person_type):
        if population:
            assert pop_size in (0, len(population.people)), "provide a population of the correct size"
            logging.warning("Using a pre-existing population - does it have the right network structure?")
            if person_type is not None:
                assert {person_type} == set(type(p) for p in population.people), \
                    "The people in this population are of the wrong type"
            population.reset_people(society)
            self.pop = population
            return population

        population_type = population_type or FixedNetworkPopulation
        person_type = person_type or PersonCovid
        return population_type(pop_size, society, person_type=person_type)

    def set_recorder(self, recorder=None):
        self.recorder = recorder or OutbreakRecorder()

    def initialize_timers(self, n_days, enc_per_day):
        self.n_days = n_days
        self.n_periods = n_days * enc_per_day
        self.time_increment = 1 / enc_per_day

        self.time = 0
        self.step_num = 0

    def simulate(self):
        for t in range(self.n_periods):
            self.update_time()
            self.society.manage_outbreak(self.pop)
            self.pop.attack_in_groupings(self.group_size)
            self.record_state()
        self.recorder.realized_r0 = self.pop.realized_r0()
        self.recorder.society_config = self.society.cfg
        self.recorder.disease_config = self.disease.cfg
        return self.recorder

    def update_time(self):
        self.pop.update_time()
        self.time += self.time_increment
        self.step_num += 1

    def record_state(self):
        # logging.info("Outbreak.record_state")
        self.recorder.record_step(self)

    def plot(self, **kwargs):
        self.recorder.plot(**kwargs)


class OutbreakRecorder:
    def __init__(self):
        self.story = []
        self.realized_r0 = None

    def record_step(self, o):

        N = len(o.pop.people)
        # logging.info(f"OutbreakRecorder.record_step, population={N}")
        # pot_haz = sum([covid_hazard(person.age) for person in o.pop.people])
        # tot_haz = sum([covid_hazard(person.age) for person in o.pop.infected()])
        all_completed_tests = [t for q in o.society.queues for t in q.completed_tests]
        step = [o.time,
                o.pop.count_infected() / N,
                o.pop.count_infectious() / N,
                len(all_completed_tests) / N / o.time_increment,
                sum(len([t for t in q.tests if t.swab_taken]) for q in o.society.queues) / N,
                sum(p.isolating for p in o.pop.people) / N,
                # len([t for t in all_completed_tests if t.positive]) / N / o.time_increment,
                # tot_haz/pot_haz,
                ]
        if o.step_num % (14 * o.society.episodes_per_day) == 1 or (o.step_num == o.n_periods):
            logging.info(f"Day {int(step[0])}, prop infected is {step[1]:2.2f}, "
                         f"prop infectious is {step[2]:2.4f}")
            if o.pop.count_infectious() > 0:
                coord = [[p.home.coordinate['lon'], p.home.coordinate['lat']] for p in o.pop.people if
                         p.infectious]
                coord_column_list = list(zip(*coord))
                heatmap, xedges, yedges = np.histogram2d(coord_column_list[0], coord_column_list[1], bins=150)
                extent = [xedges[0], xedges[-1], yedges[0], yedges[-1]]
                plt.clf()
                fig = plt.figure()
                plt.title(f'Day {int(step[0])} Infectious in simulated Leeds')
                plt.xlabel('latitude')
                plt.ylabel('longitude')
                plt.imshow(heatmap.T, extent=extent, origin='lower', vmin=0, vmax=50)
                plt.show()

        self.story.append(step)

    def plot(self, **kwargs):
        df = self.get_dataframe()
        ax = (df.drop(columns=['ever infected']) * 100).plot(grid=True, **kwargs)
        ax.set_ylabel("percent of the population")
        logging.info(f" Realized R0 of early infections is {self.realized_r0:2.2f}")
        logging.info(f" {self.story[-1][1] * 100:2.1f} percent of the proportion was infected during the epidemic")

    def get_dataframe(self):
        df = pd.DataFrame(self.story)
        df.columns = ['days of epidemic', 'ever infected', 'infectious',
                      'tested daily', 'waiting for test results', 'isolating']  # , 'daily_detected_']
        df = df.set_index('days of epidemic')
        return df
