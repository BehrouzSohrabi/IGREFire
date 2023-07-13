import numpy as np
import pandas as pd
import json
import string
import ast
import statistics
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon, box, mapping

from .messages import *
from .utils import callback, progress_bar, cell_label_generator

class Report:
    
    # Class Constructor
    def __init__(self, config, area_dx=12, area_dy=12):
        
        config.read_topology()
        config.read_scenarios()
        config.read_record()
        self.config = config
        
        self._features_in_areas(area_dx, area_dy)
        self.weathers = self._attach_weathers()

    def run(self):
        
        # Risk, Impact, and Vulnerability
        for feature in self.config.topology['features']:

            # Line
            if feature['geometry']['type'] == 'LineString' and feature['properties']['type'] == 'BRANCH':
                branch = feature['properties']['branch']

                # For each weather group
                for weather in self.weathers:
                    Z_bar_j = self.config.scenarios[
                        (self.config.scenarios['Branch'] != branch) &
                        (self.config.scenarios['Weather'] == weather)
                    ]
                    Z_j = self.config.scenarios[
                        (self.config.scenarios['Branch'] == branch) &
                        (self.config.scenarios['Weather'] == weather)
                    ]
                    feature['properties'][f'vulnerability-{weather}'] = Z_bar_j[f'Affect Branch {branch}'].mean()
                    feature['properties'][f'risk-{weather}'] = Z_j['Total Outage'].mean() / Z_j['Total Load'].mean()
                
                # AVG
                feature['properties']['vulnerability-avg'] = sum(feature['properties'][f'vulnerability-{weather}'] for weather in self.weathers) / len(self.weathers)
                feature['properties']['risk-avg'] = sum(feature['properties'][f'risk-{weather}'] for weather in self.weathers) / len(self.weathers)

            # Node
            elif feature['geometry']['type'] == 'Point':
                node = feature['properties']['bus']

                # For each weather group
                for weather in self.weathers:
                    Z = self.config.scenarios[self.config.scenarios['Weather'] == weather]
                    feature['properties'][f'vulnerability-{weather}'] = Z[f'Affect Node {node}'].mean()
                    
                    if Z[f'Bus Load {node}'].mean() > 0:
                        feature['properties'][f'impact-{weather}'] = Z[f'Bus Outage {node}'].mean() / Z[f'Bus Load {node}'].mean()
                    else:
                        feature['properties'][f'impact-{weather}'] = 0

                # AVG
                feature['properties']['vulnerability-avg'] = sum(feature['properties'][f'vulnerability-{weather}'] for weather in self.weathers) / len(self.weathers)
                feature['properties']['impact-avg'] = sum(feature['properties'][f'impact-{weather}'] for weather in self.weathers) / len(self.weathers)
            
            # Spatial Risk
            elif feature['geometry']['type'] == 'Polygon':

                # For each weather group
                for weather in self.weathers + ['avg']:

                    node_contributions, line_contributions = [], []
                    node_contribution, line_contribution = 0, 0

                    # Gather node contributions
                    for node in feature['properties']['nodes']:
                        component = self.find_feature_by_property('bus', node)
                        node_contributions.append(component['properties'][f'vulnerability-{weather}'] * component['properties'][f'impact-{weather}'])

                    # Gather line contributions
                    for line in feature['properties']['lines']:
                        component = self.find_feature_by_property('branch', line)
                        if component['properties']['type'] == 'LINK': continue
                        line_contributions.append(component['properties'][f'vulnerability-{weather}'] * component['properties'][f'risk-{weather}'])
                    
                    # # Calculate means and standard deviations
                    # if len(node_contributions) > 0:
                    #     mean_node = sum(node_contributions) / len(node_contributions)
                    #     std_dev_node = (sum((x - mean_node) ** 2 for x in node_contributions) / len(node_contributions)) ** 0.5
                    #     node_contribution = sum(((x - mean_node) / std_dev_node) if std_dev_node != 0 else 0 for x in node_contributions)

                    # if len(line_contributions) > 0:
                    #     mean_line = sum(line_contributions) / len(line_contributions)
                    #     std_dev_line = (sum((x - mean_line) ** 2 for x in line_contributions) / len(line_contributions)) ** 0.5
                    #     line_contribution = sum(((x - mean_line) / std_dev_line) if std_dev_line != 0 else 0 for x in line_contributions)

                    # Calculate min and max values
                    if len(node_contributions) > 0:
                        min_node = min(node_contributions)
                        max_node = max(node_contributions)
                        node_contribution = sum(((x - min_node) / (max_node - min_node)) if max_node != min_node else 0 for x in node_contributions)

                    if len(line_contributions) > 0:
                        min_line = min(line_contributions)
                        max_line = max(line_contributions)
                        line_contribution = sum(((x - min_line) / (max_line - min_line)) if max_line != min_line else 0 for x in line_contributions)
                    
                    # Calculate normalized spatial risk
                    feature['properties'][f'spatial-risk-{weather}'] = node_contribution + line_contribution

        # Resilience Factor
        # For each weather group
        R = {}
        for weather in self.weathers:
            Z = self.config.scenarios[self.config.scenarios['Weather'] == weather]
            Z = Z.copy()
            R[f'resilience-{weather}'] = ((Z['Total Load'] - Z['Total Outage']) / Z['Total Load']).mean()
        
        R['resilience-avg'] = statistics.mean(R.values())


        # Save Results to a CSV file
        metadata = {
            'analysis-record': self.config.id,
            'analysis-title': self.config.analysis_run_title,
        }
        metadata.update(R)
        self.config.topology['properties'] = metadata

        # Metadata
        file_records = self.config.generate_file_name('report_record')
        metadata_df = pd.DataFrame(metadata, index=[0])
        metadata_df.to_csv(file_records, index=False)

        # Lines
        file_lines = self.config.generate_file_name('report_lines')
        linestring_df = pd.DataFrame([feat['properties'] for feat in self.config.topology['features'] if feat['geometry']['type'] == 'LineString'])
        linestring_df.to_csv(file_lines, index=False)

        # Nodes
        file_nodes = self.config.generate_file_name('report_nodes')
        point_df = pd.DataFrame([feat['properties'] for feat in self.config.topology['features'] if feat['geometry']['type'] == 'Point'])
        point_df.to_csv(file_nodes, index=False)

        # Areas
        file_area = self.config.generate_file_name('report_areas')
        polygon_df = pd.DataFrame([feat['properties'] for feat in self.config.topology['features'] if feat['geometry']['type'] == 'Polygon'])
        polygon_df.to_csv(file_area, index=False)

        # Save the GeoJSON data to a file
        file_gis = self.config.generate_file_name('report_gis')
        with open(file_gis, 'w') as f:
            json.dump(self.config.topology, f)
        
        # Save scenarios GeoJSON data to a file
        features = []
        for _, row in self.config.scenarios.iterrows():
            point = Point(row['Ignition Point X'], row['Ignition Point Y'])
            properties = row.drop(['Ignition Point X', 'Ignition Point Y']).to_dict()
            point = json.loads(json.dumps(mapping(point)))
            features.append({"type": "Feature", "properties": properties, "geometry": point})
        feature_collection = {"type": "FeatureCollection", "features": features}
        file_scenarios = self.config.generate_file_name('scenarios_gis')
        with open(file_scenarios, 'w') as f:
            json.dump(feature_collection, f)

        callback('', '\nAnalysis Finished.\nGenerated Reports:')
        print('  - Analysis Records Updated: \t' + file_records)
        print('  - Lines Metrics Dataframe: \t' + file_lines)
        print('  - Nodes Metrics Dataframe: \t' + file_nodes)
        print('  - Areas Metrics Dataframe: \t' + file_area)
        print('  - Ignitions Points geoJSON: \t' + file_scenarios)
        print('  - Topology Metrics geoJSON: \t' + file_gis)

    # Break down json dict in features into separate columns
    def _normalize_json_column(self, df, keys):
        for key in keys:
            flattened = pd.json_normalize(df[key])
            flattened.columns = f'{key}-' + flattened.columns
            df = pd.concat([df.drop(key, axis=1), flattened], axis=1)
        return df
    
    # Split Area and Find Features in them
    def _features_in_areas(self, ndx, ndy):
        xmin, ymin, xmax, ymax = self.config.landscape_bounds
        dx = (xmax - xmin) / ndx
        dy = (ymax - ymin) / ndy
        grid = []

        for xi, x in enumerate(np.arange(xmin, xmax, dx)):
            gen = cell_label_generator()
            for y in np.arange(ymin, ymax, dy):
                cell = box(x, y, x+dx, y+dy)
                label = next(gen) + str(int(xi + 1))
                grid.append({"box": cell, "nodes": [], "lines": [], "label": label})

        # Convert GeoJSON features to Shapely geometries
        points = [{'id': feat['properties']['bus'], 'geometry': Point(feat['geometry']['coordinates'])} for feat in self.config.topology['features'] if feat['geometry']['type'] == 'Point']
        lines = [{'id': feat['properties']['branch'], 'geometry': LineString(feat['geometry']['coordinates'])} for feat in self.config.topology['features'] if feat['geometry']['type'] == 'LineString']

        # now, each cell in grid is a Polygon object
        for cell in grid:
            cell['nodes'] = [pt['id'] for pt in points if cell['box'].contains(pt['geometry']) or cell['box'].intersects(pt['geometry'])]
            cell['lines'] = [line['id'] for line in lines if cell['box'].contains(line['geometry']) or cell['box'].intersects(line['geometry'])]

            # add to geojson topology
            self.config.topology['features'].append({
                "type": "Feature",
                "geometry": mapping(cell['box']),
                "properties": {
                    "nodes": cell['nodes'],
                    "lines": cell['lines'],
                    "label": cell['label']
                }
            })
    
    # Make a list of weathers used in the analysis
    def _attach_weathers(self):
        return list(ast.literal_eval(self.config.record['weather_files']).keys()) + list(ast.literal_eval(self.config.record['weather_conditions']).keys())

    def find_feature_by_property(self, property_name, value):
        for feature in self.config.topology['features']:
            if feature['properties'].get(property_name) == value:
                return feature
        return None