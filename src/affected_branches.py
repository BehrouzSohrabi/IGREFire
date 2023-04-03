import rasterio

from .messages import *
from .utils import callback, progress_bar, traverse_branch

class AffectedBranches:

    # Class Constructor
    def __init__(self, config):

        self.config = config

        # Interpolate points on each branch
        self.points = traverse_branch(
            config.topology,
            config.geod,
            points_number = 0,
            points_distance = config.farsite_perimeter_resolution
        )
        self.scenarios = self.config.read_scenarios()
    
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

    def _lines_on_fire(self, intensity_raster):

        # Read the intensity raster
        intensity_array = self._read_raster(intensity_raster)

        # Find lines affected by fire
        affected_lines = {}

        for branch in self.points:
            branch_key = f'Affect Branch {branch["branch_id"]}'
            affected_lines[branch_key] = False
            for point in branch['branch_points']:
                row, col = self._point_to_raster_index(point.x, point.y, intensity_array.shape)
                intensity = intensity_array[row, col]
                if intensity > self.config.intensity_threshold:
                    affected_lines[branch_key] = True
                    break

        return affected_lines

    # Match topology GeoJSON and FARSITE raster outputs
    def find(self):
        
        callback('update', AFFECTED_BRANCHES_STARTED)

        print() # wrap progress bar

        # Iterate over scenarios
        for index, row in self.scenarios.iterrows():

            # Show progress bar
            id = index+1
            description = AFFECTED_BRANCHES_DESCRIPTION.format(id, row["Branch"], row["Ignition Point"], row["Title"])
            progress_bar(id, self.config.scenarios, prefix='Progress:', description=description)

            # Read Intensity.asc file and convert it to a numpy array
            raster_file = f'{row["Run Directory"]}{self.config.FARSITE_intensity_file}'
            affected_lines = self._lines_on_fire(raster_file)

            # Append affected branches info to scenario df
            for key, value in affected_lines.items():
                self.scenarios.at[index, key] = value

        print()

        # Update Analysis Status
        callback('update', AFFECTED_BRANCHES_FINISHED)

        # Update Analysis Records
        self.scenarios.to_csv(self.config.scenarios_file, index=False)
        self.config.update_record(status='Affected Branches Finished')
    
    def prepare(self):

        # Iterate over scenarios
        for index, row in self.scenarios.iterrows():
        
        