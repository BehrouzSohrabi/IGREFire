import numpy as np
import pandas as pd
import json
import ast
import statistics
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon, box, mapping

from .messages import *
from .utils import callback, progress_bar

class Report:
    
    # Class Constructor
    def __init__(self, config):
        
        config.read_topology()
        config.read_scenarios()
        config.read_record()
        self.config = config
    
    def find_feature_by_property(self, property_name, value):
        for feature in self.config.topology['features']:
            if feature['properties'].get(property_name) == value:
                return feature
        return None

    def run(self, area_dx=10, area_dy=10):

        areas = self._features_in_areas(area_dx, area_dy)
        weathers = list(ast.literal_eval(self.config.record['weather_files']).keys()) + list(ast.literal_eval(self.config.record['weather_conditions']).keys())
        
        # Risk, Impact, and Vulnerability
        for feature in self.config.topology['features']:

            # Line
            if feature['geometry']['type'] == 'LineString' and feature['properties']['type'] == 'BRANCH':
                branch = feature['properties']['branch']

                # For each weather group
                for weather in weathers:
                    Z_bar_j = self.config.scenarios[
                        (self.config.scenarios['Branch'] != branch) &
                        (self.config.scenarios['Weather'] == weather)
                    ]
                    Z_j = self.config.scenarios[
                        (self.config.scenarios['Branch'] == branch) &
                        (self.config.scenarios['Weather'] == weather)
                    ]
                    feature['properties'][f'vulnerability-{weather}'] = Z_bar_j[f'Affect Branch {branch}'].mean()
                    feature['properties'][f'risk-{weather}'] = Z_j['Total Outage'].mean()
                
                # AVG
                feature['properties']['vulnerability-avg'] = sum(feature['properties'][f'vulnerability-{weather}'] for weather in weathers) / len(weathers)
                feature['properties']['risk-avg'] = sum(feature['properties'][f'risk-{weather}'] for weather in weathers) / len(weathers)

            # Node
            elif feature['geometry']['type'] == 'Point':
                node = feature['properties']['bus']

                # For each weather group
                for weather in weathers:
                    Z = self.config.scenarios[self.config.scenarios['Weather'] == weather]
                    feature['properties'][f'vulnerability-{weather}'] = Z[f'Affect Node {node}'].mean()
                    feature['properties'][f'impact-{weather}'] = Z_j[f'Bus Outage {node}'].mean()

                # AVG
                feature['properties']['vulnerability-avg'] = sum(feature['properties'][f'vulnerability-{weather}'] for weather in weathers) / len(weathers)
                feature['properties']['impact-avg'] = sum(feature['properties'][f'impact-{weather}'] for weather in weathers) / len(weathers)
            
            # Spatial Risk
            elif feature['geometry']['type'] == 'Polygon':

                # For each weather group
                for weather in weathers + ['avg']:
                    feature['properties'][f'spatial-risk-{weather}'] = 0

                    for line in feature['properties']['lines']:
                        component = self.find_feature_by_property('branch', line)
                        if component['properties']['type'] == 'LINK': continue
                        feature['properties'][f'spatial-risk-{weather}'] += component['properties'][f'vulnerability-{weather}'] * component['properties'][f'risk-{weather}']
                    
                    for node in feature['properties']['nodes']:
                        component = self.find_feature_by_property('bus', node)
                        feature['properties'][f'spatial-risk-{weather}'] += component['properties'][f'vulnerability-{weather}'] * component['properties'][f'impact-{weather}']
        

        # Resilience Factor
        # For each weather group
        R = {}
        for weather in weathers:
            Z = self.config.scenarios[self.config.scenarios['Weather'] == weather]
            Z = Z.copy()
            Z.loc[:, 'Total Load'] = Z.loc[:, Z.columns.str.startswith('Bus Load')].sum(axis=1) # This line can be removed. It's done in matpower module
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
        metadata_df = pd.DataFrame(metadata, index=[0])
        metadata_df.to_csv(self.config.generate_file_name('report_record'), index=False)

        # Lines
        linestring_df = pd.DataFrame([feat['properties'] for feat in self.config.topology['features'] if feat['geometry']['type'] == 'LineString'])
        linestring_df.to_csv(self.config.generate_file_name('report_lines'), index=False)

        # Nodes
        point_df = pd.DataFrame([feat['properties'] for feat in self.config.topology['features'] if feat['geometry']['type'] == 'Point'])
        point_df.to_csv(self.config.generate_file_name('report_nodes'), index=False)

        # Areas
        polygon_df = pd.DataFrame([feat['properties'] for feat in self.config.topology['features'] if feat['geometry']['type'] == 'Polygon'])
        polygon_df.to_csv(self.config.generate_file_name('report_areas'), index=False)

        # Save the GeoJSON data to a file
        with open(self.config.generate_file_name('report_gis'), 'w') as f:
            json.dump(self.config.topology, f)
        
        # Save scenarios GeoJSON data to a file
        features = []
        for _, row in self.config.scenarios.iterrows():
            point = Point(row['Ignition Point X'], row['Ignition Point Y'])
            properties = row.drop(['Ignition Point X', 'Ignition Point Y']).to_dict()
            point = json.loads(json.dumps(mapping(point)))
            features.append({"type": "Feature", "properties": properties, "geometry": point})
        feature_collection = {"type": "FeatureCollection", "features": features}
        with open(self.config.generate_file_name('scenarios_gis'), 'w') as f:
            json.dump(feature_collection, f)

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

        for x in np.arange(xmin, xmax, dx):
            for y in np.arange(ymin, ymax, dy):
                cell = box(x, y, x+dx, y+dy)
                grid.append({"box": cell, "nodes": [], "lines": []})

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
                }
            })
        
        return grid