import tkinter as tk
from tkinter import ttk
from .config import Config
from .analysis import Analysis

class AnalysisGUI(tk.Tk):
    def __init__(self, config):
        super().__init__()

        # Get Initial Config
        self.config = config

        # Configure window
        self.title("IGREFire")
        self.geometry("800x600")

        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create input tab and result tab
        self.input_tab = ttk.Frame(self.notebook)
        self.result_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.input_tab, text="Input")
        self.notebook.add(self.result_tab, text="Result")

        # Create input form on input tab
        self._create_input_form()

        # Create progress bar and progress text
        self.progress = ttk.Progressbar(self.input_tab, mode="indeterminate")
        self.progress.grid(column=0, row=16, columnspan=2, pady=10)
        self.progress_text = ttk.Label(self.input_tab, text="")
        self.progress_text.grid(column=0, row=17, columnspan=2)

        # Create result table on result tab
        self._create_result_table()

    def _create_input_form(self):
        # Create input labels
        analysis_run_title_label = ttk.Label(self.input_tab, text="Analysis Run Title")
        test_system_topology_label = ttk.Label(self.input_tab, text="Test System Topology (GeoJSON)")
        test_system_matpower_label = ttk.Label(self.input_tab, text="Test System Matpower")
        landscape_file_label = ttk.Label(self.input_tab, text="Landscape File (LCP)")
        landscape_bounds_label = ttk.Label(self.input_tab, text="Landscape Bounds [W, S, E, N]")
        landscape_resolution_label = ttk.Label(self.input_tab, text="Landscape Resolution (m)")
        farsite_perimeter_resolution_label = ttk.Label(self.input_tab, text="FARSITE Resolution (m)")
        farsite_time_step_label = ttk.Label(self.input_tab, text="FARSITE Timestep (min)")
        fuel_moistures_label = ttk.Label(self.input_tab, text="Fuel Moistures")
        weather_files_label = ttk.Label(self.input_tab, text="Weather Files")
        barriers_file_label = ttk.Label(self.input_tab, text="Barriers File (optional)")
        crown_fire_method_label = ttk.Label(self.input_tab, text="Crown Fire Method")
        ignition_points_number_label = ttk.Label(self.input_tab, text="Ignition Points Number")
        ignition_points_distance_label = ttk.Label(self.input_tab, text="Ignition Points Distance (m, optional)")
        ignition_points_radius_label = ttk.Label(self.input_tab, text="Ignition Points Radius (m)")

        # Create input entry widgets
        self.analysis_run_title_entry = ttk.Entry(self.input_tab)
        self.test_system_topology_entry = ttk.Entry(self.input_tab)
        self.test_system_matpower_entry = ttk.Entry(self.input_tab)
        self.landscape_file_entry = ttk.Entry(self.input_tab)
        self.landscape_bounds_entry = ttk.Entry(self.input_tab)
        self.landscape_resolution_entry = ttk.Entry(self.input_tab)
        self.farsite_perimeter_resolution_entry = ttk.Entry(self.input_tab)
        self.farsite_time_step_entry = ttk.Entry(self.input_tab)
        self.fuel_moistures_entry = ttk.Entry(self.input_tab)
        self.weather_files_entry = ttk.Entry(self.input_tab)
        self.barriers_file_entry = ttk.Entry(self.input_tab)
        self.crown_fire_method_entry = ttk.Entry(self.input_tab)
        self.ignition_points_number_entry = ttk.Entry(self.input_tab)
        self.ignition_points_distance_entry = ttk.Entry(self.input_tab)
        self.ignition_points_radius_entry = ttk.Entry(self.input_tab)

        # Place input labels and entry widgets on the input_tab using grid layout
        row = 0
        for label, entry in zip(
            [
                analysis_run_title_label,
                test_system_topology_label,
                test_system_matpower_label,
                landscape_file_label,
                landscape_bounds_label,
                landscape_resolution_label,
                farsite_perimeter_resolution_label,
                farsite_time_step_label,
                fuel_moistures_label,
                weather_files_label,
                barriers_file_label,
                crown_fire_method_label,
                ignition_points_number_label,
                ignition_points_distance_label,
                ignition_points_radius_label,
            ],
            [
                self.analysis_run_title_entry,
                self.test_system_topology_entry,
                self.test_system_matpower_entry,
                self.landscape_file_entry,
                self.landscape_bounds_entry,
                self.landscape_resolution_entry,
                self.farsite_perimeter_resolution_entry,
                self.farsite_time_step_entry,
                self.fuel_moistures_entry,
                self.weather_files_entry,
                self.barriers_file_entry,
                self.crown_fire_method_entry,
                self.ignition_points_number_entry,
                self.ignition_points_distance_entry,
                self.ignition_points_radius_entry,
            ]):
                label.grid(row=row, column=0, sticky="e")
                entry.grid(row=row, column=1, sticky="w")
                row += 1

        # Create "Analyze" button
        analyze_button = ttk.Button(self.input_tab, text="Analyze", command=self._run_analysis)
        analyze_button.grid(column=0, row=row, columnspan=2)

    def _check_inputs(self):
        # Check the inputs and create a new config
        # Needs to read the inputs
        # Then create config with: config = Config(config_inputs, ...)
        config = self.config
        return config

    def _run_analysis(self, config):
        # Get input values from the form
        # ...
        config = self._check_inputs()

        # Create a Analysis object with the config
        self.analysis = Analysis(config)

        # Start the analysis and update the progress bar and progress text
        self.progress.start()
        self.progress_text.config(text="Running analysis...")

        # Run the analysis
        result = self.analysis.run()

        # Update progress bar and progress text after the analysis is finished
        self.progress.stop()
        self.progress_text.config(text="Analysis completed")

        # Show the result in the result table
        self._show_result(result)

    def _create_result_table(self):
        # Create a table (tree view) on the result_tab to display the results
        # ...
        pass

    def _show_result(self, result):
        # Populate the result table with the analysis result data
        # ...
        pass

    def launch(self):
        # Create the main window.
        root = tk.Tk()
        root.title(self.title)
        root.withdraw()

        # Add input fields, labels, buttons, and progress bar.
        # ...

        # Start the main loop.
        root.mainloop()