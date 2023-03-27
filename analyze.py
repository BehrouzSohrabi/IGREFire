from cases import build_cases
from fire import run_fire_spread
from topology import modify_topology
from powerflow import run_powerflow
from report import create_report, visualize

if __name__ == '__main__':

    # Analysis Inputs
    test_system = 'IEEE_30_bus_system' # test system file prefix
    resolution = 60 # landscape resolution, 30 or 60 meters per pixel
    save_result = True

    # Set Up Scenario Cases Matrix
    fire_model = 'FARSITE'
    fire_steps_length = 10 # per length, -1 for init fire by number
    fire_steps_number = -1 # per line, -1 for init fire by length
    fire_initial_size = [5, 10, 20] # radius of initial fire object file, meters
    wind_direction = [0, 90, 180, 270] # degrees
    wind_intensity = [0, 1, 2, 3] # mph
    humidity = [80, 90] # relative humidity, %

    # Build Cases
    cases = build_cases(
        fire_steps_length, fire_steps_number, fire_initial_size,
        wind_direction, wind_intensity, humidity
    )

    # Run Fire Spread Simulator
    fire_spread = run_fire_spread(fire_model, resolution, cases)

    # Modify Powerflow data
    topology = modify_topology(fire_spread)

    # Run Powerflow Analysis
    powerflow_output = run_powerflow(test_system, topology)

    # Create Report
    risk, vulnerability = create_report(cases, fire_spread, topology, powerflow_output, save_result)

    # Visualize Reports
    visualize(topology, risk, save_result)
    visualize(topology, vulnerability, save_result)