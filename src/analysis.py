import sys

from .inputs import Inputs
from .FARSITE import FARSITE
from .MATPOWER import MATPOWER
from .powerflow import PowerFlow
from .utils import callback

class Analysis:
    def __init__(self, config):
        self.config = config

    def _generate_inputs(self):
        self.inputs = Inputs(self.config)
        self.inputs.generate()

    def _run_simulations(self):
        self.simulations = FARSITE(self.config)
        self.simulations.run()

    def _prepare_matpower(self):
        self.matpower = MATPOWER(self.config)
        self.matpower.prepare()

    def _run_powerflow(self):
        self.powerflow = PowerFlow(self.config)
        self.powerflow.run()

    def run(self):
        self._generate_inputs()
        self._run_simulations()
        self._prepare_matpower()
        self._run_powerflow()