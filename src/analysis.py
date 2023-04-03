import sys

from .inputs_generator import InputsGenerator
from .FARSITE import FARSITE
from .affected_branches import AffectedBranches
from .powerflow_analysis import PowerFlow
from .report import Report
from .utils import callback

class Analysis:
    def __init__(self, config):
        self.config = config

    def _prepare_inputs(self):
        self.inputs = InputsGenerator(self.config)
        self.inputs.generate()

    def _run_simulations(self):
        self.simulations = FARSITE(self.config)
        self.simulations.run()

    def _prepare_matpower(self):
        self.matpower = AffectedBranches(self.config)
        # self.matpower.find()
        self.matpower.prepare()

    def _run_powerflow(self):
        self.powerflow = PowerFlow(self.config)
        self.powerflow.run()

    def _visualize_results(self):
        self.report = Report(self.config)
        self.report.visualize()

    def run(self):
        self._prepare_inputs()
        self._run_simulations()
        self._prepare_powerflow()
        self._run_powerflow()
        self._visualize_results()