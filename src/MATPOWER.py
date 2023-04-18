from os.path import isfile
import rasterio
import pandas as pd
import numpy as np
import string

from .messages import *
from .utils import callback, progress_bar, traverse_branch

class MATPOWER:

    # Class Constructor
    def __init__(self, config):

        self.config = config
        self.scenarios = self.config.read_scenarios()

        # Interpolate points on each branch
        self.points = traverse_branch(
            config.topology,
            config.geod,
            points_number = 0,
            points_distance = config.farsite_perimeter_resolution
        )
    
    # Convert coordinates to row, column indices in the numpy array
    def _point_to_raster_index(self, x, y, shape):
        xmin, ymin, xmax, ymax = self.config.landscape_bounds
        row = int(shape[0]*((ymax-y)/(ymax-ymin)))
        col = int(shape[1]*((x-xmin)/(xmax-xmin)))
        return row, col

    def _read_raster(self, file_path):
        raster = rasterio.open(file_path)
        array = raster.read(1)
        return array

    def _branches_on_fire(self, intensity_raster):

        # Read the intensity raster
        if not isfile(intensity_raster): return {}
        intensity_array = self._read_raster(intensity_raster)

        # Find branches affected by fire
        affected_branches = {}
        branches = self.config.matpower['branch']
        gens = [int(gen[0]) for gen in self.config.matpower['gen']]

        # Iterate over points on all branches
        for branch in self.points:
            branch_key = branch["branch_id"]
            affected_branches[branch_key] = False
            for point in branch['branch_points']:
                row, col = self._point_to_raster_index(point.x, point.y, intensity_array.shape)
                intensity = intensity_array[row, col]
                if intensity > self.config.intensity_threshold:
                    affected_branches[branch_key] = True
                    break

        # Find disconnected branches that were connected to the affected branches
        connected_branches = [branch for index, branch in enumerate(branches, start=1) if index not in affected_branches or not affected_branches[index]]

        # Create adjacency list
        graph = {}
        for branch in connected_branches:
            graph.setdefault(int(branch[0]), []).append(int(branch[1]))
            graph.setdefault(int(branch[1]), []).append(int(branch[0]))

        # DFS to find reachable nodes
        def dfs(graph, node, visited):
            if node not in visited:
                visited.add(node)
                for neighbor in graph.get(node, []):
                    dfs(graph, neighbor, visited)
            return visited
        # Find reachable nodes for each head node and merge them
        reachable_nodes = set()
        for head_node in gens:
            reachable_nodes |= dfs(graph, head_node, set())

        # Update affected_branches dictionary
        for index, branch in enumerate(branches, start=1):
            if index in affected_branches and not affected_branches[index]:
                fbus, tbus = branch[0], branch[1]
                if fbus not in reachable_nodes or tbus not in reachable_nodes:
                    affected_branches[index] = True

        return affected_branches

    def _find_affected_nodes(self, affected_branches):

        # Find nodes connected to affected branches
        affected_nodes = {}
        branches = self.config.matpower['branch']

        # Iterate over branches to check if their nodes were affected
        for index, branch in enumerate(branches, start=1):
            fbus, tbus = int(branch[0]), int(branch[1])
            affected_nodes.setdefault(fbus, False)
            affected_nodes.setdefault(tbus, False)
            if index in affected_branches and affected_branches[index]:
                affected_nodes[fbus] = True
                affected_nodes[tbus] = True
        
        return affected_nodes

    def _format_array_string(self, arr, precision=2):
    
        # Check if all the numbers in a column have zero after the precision point
        def is_column_int(arr, col):
            col_values = arr[:, col]
            return np.allclose(col_values % 1, 0)
        
        # Get a list of columns that have all integers
        arr = np.array(arr)
        int_columns = [is_column_int(arr, col) for col in range(arr.shape[1])]

        # Format the array
        formatted_arr = np.empty(arr.shape, dtype=object)
        for r in range(arr.shape[0]):
            for c in range(arr.shape[1]):
                if int_columns[c]:
                    formatted_arr[r, c] = f"{arr[r, c]:.0f}"
                else:
                    formatted_arr[r, c] = f"{arr[r, c]:.{precision}f}"
        
        # Convert the formatted array to a string
        arr_str = ''
        for i, row in enumerate(formatted_arr):
            arr_str += '\t\t[' + ', \t'.join(row) + f'], #{i+1}\n'
        arr_str = arr_str[:-1]

        return arr_str
    
    def _generate_matpower(self, scenario, affected_branches, degrade_factor = .99):

        def save_matpower(modified_branch, file_type, isolated_nodes):

            # Slack bus can't be isolated
            slack_bus_id = [bus[0] for bus in buses if bus[1] == 3][0]
            isolated_nodes = [bus_id for bus_id in isolated_nodes if bus_id != slack_bus_id]

            # Modify buses and remove isolated buses
            modified_buses = [bus for bus in buses if bus[0] not in isolated_nodes]

            # Modify generator data
            modified_gen = [gen for gen in gens if gen[0] not in isolated_nodes]
            modified_gen_cost = [cost for i, cost in enumerate(gen_costs) if gens[i][0] not in isolated_nodes]

            # Iterate over buses to add virtual a high-cost generator if the bus has any load
            for bus in modified_buses:
                bus_i, Pd, Qd = bus[0], bus[2], bus[3]
                if Pd > 0:
                    modified_gen = np.append(modified_gen, [[bus_i, 0, 0, Qd*1.5, -Qd*.5, 1, self.config.matpower['baseMVA'], 1, Pd, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]], axis=0)
                    modified_gen_cost = np.append(modified_gen_cost, [[2, 0, 0, 3, 9999, 0, 0]], axis=0)

            # Substitute the placeholders with the actual values and Write the output to a new file
            _, extension, case_name = self.config.read_MATPOWER_path()
            file_name = self.config.generate_file_name(f'MATPOWER_{file_type}', weather=scenario['Weather'], branch_id=scenario['Branch'], point_id=scenario['Ignition Point'], matpower_file=f'{case_name}{extension}')

            params = {
                'case_name': f'{file_type}_{case_name}',
                'version': self.config.matpower['version'],
                'baseMVA': self.config.matpower['baseMVA'],
                'bus': self._format_array_string(modified_buses),
                'gen': self._format_array_string(modified_gen),
                'branch': self._format_array_string(modified_branch),
                'areas': self._format_array_string(areas),
                'gencost': self._format_array_string(modified_gen_cost, precision=4)
            }

            # Save modified MATPOWER with new parameters using the template
            with open(self.config.MATPOWER_template, 'r') as f:
                template = string.Template(f.read())
            with open(file_name, 'w') as f:
                f.write(template.substitute(params))

        # Unpack data
        buses, branches, gens, gen_costs, areas = self.config.matpower['bus'], self.config.matpower['branch'], self.config.matpower['gen'], self.config.matpower['gencost'], self.config.matpower['areas']

        # Find the branches that are not out
        active_branches = [branch[:2] for index, branch in enumerate(branches, start=1) if not affected_branches.get(index, False)]

        # Extract active nodes from active_branches
        active_nodes = set(int(node) for branch in active_branches for node in branch)

        # Find all nodes from the branches
        all_nodes = set(int(node) for branch in branches for node in branch[:2])

        # Find isolated nodes and redundant branches
        isolated_nodes = all_nodes - active_nodes
        redundant_branches = [index for index, branch in enumerate(branches, start=1) if any(node in isolated_nodes for node in branch[:2])]

        # Branch effect scenarios
        for branch_effect in self.config.branch_effects:
            branch_rows = []

            # Check for each branch if it's being affected
            for index, row in enumerate(branches, start=1):

                # Change the status or capacity of branch accordingly
                if affected_branches.get(index, False):
                    if branch_effect == 'trip':
                        if index not in redundant_branches:
                            branch_row = row.copy()
                            branch_row[10] = 0 # status = 0 (out of service)
                            branch_rows.append(branch_row)
                    else:
                        branch_row = row.copy()
                        branch_row[5] *= 1-degrade_factor  # Reduce rateA
                        branch_row[6] *= 1-degrade_factor  # Reduce rateB
                        branch_row[7] *= 1-degrade_factor  # Reduce rateC
                        branch_rows.append(branch_row)
                else:
                    branch_rows.append(row.copy())
            
            # Save modified MATPOWER
            save_matpower(branch_rows, branch_effect, isolated_nodes)

    # Match topology GeoJSON and FARSITE raster outputs
    def prepare(self):
        
        def process_scenario(affected_branches, affected_nodes):
            scenario_data = {}

            # Append affected branches info to scenario df
            for idx, value in affected_branches.items():
                scenario_data[f'Affect Branch {idx}'] = value

            # Append affected nodes info to scenario df
            for idx, value in affected_nodes.items():
                scenario_data[f'Affect Node {idx}'] = value

            scenario_data['# Affected Branches'] = int(sum(value for value in affected_branches.values() if value is True))
            scenario_data['# Affected Nodes'] = int(sum(value for value in affected_nodes.values() if value is True))

            return scenario_data

        # Start preparing MATPOWER files
        callback('update', MATPOWER_PREPARATION_STARTED)

        print() # wrap progress bar

        # Iterate over scenarios
        scenario_list = []
        for index, row in self.scenarios.iterrows():

            # Show progress bar
            id = index+1
            # if id != 1: continue
            description = MATPOWER_PREPARATION_DESCRIPTION.format(id, row["Branch"], row["Ignition Point"], row["Weather"])
            progress_bar(id, self.config.scenarios, prefix='Progress:', description=description)

            # Read Intensity.asc file and convert it to a numpy array
            raster_file = f'{row["Run Directory"]}{self.config.FARSITE_intensity_file}'
            affected_branches = self._branches_on_fire(raster_file)
            affected_nodes = self._find_affected_nodes(affected_branches)

            # Generate a modified MATPOWER File for the scenario
            self._generate_matpower(row, affected_branches)

            scenario_data = process_scenario(affected_branches, affected_nodes)
            scenario_list.append(scenario_data)

        print() # wrap progress bar

        # Drop any old columns
        cols_to_remove = self.scenarios.filter(regex='^(# Affected|Affect)').columns
        self.scenarios = self.scenarios.drop(columns=cols_to_remove)

        # Only add columns from scenario_df that do not already exist
        scenario_df = pd.DataFrame(scenario_list)
        self.scenarios = pd.concat([self.scenarios, scenario_df.loc[:, ~scenario_df.columns.isin(self.scenarios.columns)]], axis=1)

        # Update Analysis Records with new raster and geojson overlap output data (affecting nodes and branches)
        self.scenarios.to_csv(self.config.scenarios_file, index=True)
        self.config.update_record(status='Affected Branches Finished')

        # Update Analysis Status
        callback('update', MATPOWER_PREPARATION_FINISHED)