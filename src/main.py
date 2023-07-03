import sys

from .inputs import Inputs
from .FARSITE import FARSITE
from .MATPOWER import MATPOWER
from .powerflow import PowerFlow
from .report import Report
from .utils import callback

class Analysis:
    def __init__(self, config):
        self.config = config

    def _generate_inputs(self):
        self.inputs = Inputs(self.config)
        self.inputs.generate()

    def _run_simulations(self, impact_file=''):
        self.simulations = FARSITE(self.config)
        self.simulations.run(impact_file)

    def _prepare_matpower(self, impact_file=''):
        self.matpower = MATPOWER(self.config)
        self.matpower.prepare(impact_file)

    def _run_powerflow(self):
        self.powerflow = PowerFlow(self.config)
        self.powerflow.run()

    def _report(self):
        self.report = Report(self.config)
        self.report.run()

    def run(self, impact_file=''):
        self._generate_inputs()
        self._run_simulations(impact_file)
        self._prepare_matpower(impact_file)
        self._run_powerflow()
        self._report()