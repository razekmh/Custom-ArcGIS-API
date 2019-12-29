import collections
import copy
import credentials as cred
import geopandas as gpd
import json
import logging
import pandas as pd
import time
import traceback
import re

from arcgis.gis import GIS
from arcgis.features import FeatureLayer
from arcgis.features import FeatureLayerCollection
from arcgis.mapping import WebMap
from copy import deepcopy
from logging.handlers import RotatingFileHandler
from pandas import read_csv
from pprint import pprint


# intiate the logger and format it 
logger = logging.getLogger("update")
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler("Logs/update_log.txt", maxBytes=1000000, backupCount=200)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def print_text_log(text_body):
    # print and logging function 
    print(text_body)
    logger.debug(str(text_body))

# mark the start of the log
logger.debug('- - - - - - NEW LOG STARTS HERE - - - - - -')

gis = GIS("https://www.arcgis.com", cred.user, cred.password)
print_text_log("Loggin in complete!")


def upload_publish(item_file_location, title='title', tags='tags'):
    # log in and upload a shapfile and then publish it as a serivce
    
    item_properties = {
    'title': title ,
    'tags': tags ,
    'type': 'Shapefile'
    }

    item_shp = gis.content.add(item_properties, data=item_file_location)
    published_layer_item = item_shp.publish()

    return published_layer_item

def create_views_columns(item_file_location, csv_file_location, feature_layer_item, col_filter=None):
    # create views and return dict of the view codes and ids

    # read geodataframe from zip file 
    gdf = gpd.read_file(r'/vsizip/'+item_file_location)
    
    # apply filter or jsut remove geometry from geodataframe col list if no filter provided 
    if filter: 
        col_list = [x for x in list(gdf.keys()) if col_filter in x]
    else: 
        col_list = [x for x in list(gdf.keys()) if not x == 'geometry']

    # read csv file of the col hierarchy
    df = pd.read_csv(csv_file_location)

    # filter to the cols where views are required 
    df = df[['Name','New_Code','Order']][df['has_view'] == 'yes']

    # sort according to the provided order of the col\
    #  as this order will be the same when adding the views to the map
    df = df.sort_values(by='Order',ascending=False)

    # create dic of the col name and code to use the name in the map display\
    # and the code for the views' names
    df_dict = pd.Series(df.Name.values,index=df.New_Code).to_dict()

    if not len(set(df['New_Code']) - set(col_list)) == 0 or not len(set(col_list) - set(df['New_Code'])) == 0: 
        return ("ERROR, Please check the consistancy of the columns in the shapfile and the csv!")

    flc = FeatureLayerCollection.fromitem(feature_layer_item)

    # create new view for each col and fill the views dict
    views_dict = {}
    base_time = time.time()

    for key, value in df_dict.items():
        loop_time = time.time()
        views_dict[key] = (flc.manager.create_view(name='view_'+key, capabilities='Query, Update, Delete')).id
        print_text_log (f"time to create {str(key)} is {str(time.time() - loop_time)}")

    print_text_log (f'full time = {str(time.time() - base_time)}')

    # change the name of each view to the name of the col instead of the code
    failed_views = []
    for key, value in views_dict.items():
        try :
            gis.content.get(views_dict[key]).layers[0].manager.update_definition({'name':df_dict[key].split('Colour Bin ')[1].strip()})
        except: 
            failed_views.append(key)
    
    if not len(failed_views) == 0:
        return("ERROR, please check the layer service")

    return views_dict


def create_map_add_views(views_dict, web_map_title ='web map title', web_map_snippet = 'web map snippet',web_map_tags = 'web map tags'):
    # create a map and add the views to it and then set the visibility of all them to false
    
    # create empty map
    web_map = WebMap()

    # add views to the map 
    for key, value in views_dict.items():
        print (key)
        map_renderer = {"renderer": "autocast", #This tells python to use JS autocasting
                    "type": "classBreaks",
                    "field":key,
                    "minValue":1}
        
        map_renderer["visualVariables"] = [{"type": "sizeInfo",
                                            "expression": "view.scale",
                                            "field": key,
                                            "stops": [  
                                                        {
                                                            "size": 1.5,
                                                            "value": 50921
                                                        },
                                                        {
                                                            "size": 0.75,
                                                            "value": 159129
                                                        },
                                                        {
                                                            "size": 0.375,
                                                            "value": 636517
                                                        },
                                                        {
                                                            "size": 0,
                                                            "value": 1273034
                                                        }
                                                    ]
                                            }]

        map_renderer["classBreakInfos"] = [{
                                    "symbol": {
                                        "color": [
                                            90,
                                            106,
                                            56,
                                            255
                                        ],
                                        "outline": {
                                            "color": [
                                                194,
                                                194,
                                                194,
                                                64
                                            ],
                                            "width": 0.75,
                                            "type": "esriSLS",
                                            "style": "esriSLSSolid"
                                        },
                                        "type": "esriSFS",
                                        "style": "esriSFSSolid"
                                    },
                                    "label": "1",
                                    "classMaxValue": 1
                                },
                                {
                                    "symbol": {
                                        "color": [
                                            117,
                                            144,
                                            67,
                                            255
                                        ],
                                        "outline": {
                                            "color": [
                                                194,
                                                194,
                                                194,
                                                64
                                            ],
                                            "width": 0.75,
                                            "type": "esriSLS",
                                            "style": "esriSLSSolid"
                                        },
                                        "type": "esriSFS",
                                        "style": "esriSFSSolid"
                                    },
                                    "label": "2",
                                    "classMaxValue": 2
                                },
                                {
                                    "symbol": {
                                        "color": [
                                            143,
                                            178,
                                            77,
                                            255
                                        ],
                                        "outline": {
                                            "color": [
                                                194,
                                                194,
                                                194,
                                                64
                                            ],
                                            "width": 0.75,
                                            "type": "esriSLS",
                                            "style": "esriSLSSolid"
                                        },
                                        "type": "esriSFS",
                                        "style": "esriSFSSolid"
                                    },
                                    "label": "3",
                                    "classMaxValue": 3
                                },
                                {
                                    "symbol": {
                                        "color": [
                                            200,
                                            223,
                                            158,
                                            255
                                        ],
                                        "outline": {
                                            "color": [
                                                194,
                                                194,
                                                194,
                                                64
                                            ],
                                            "width": 0.75,
                                            "type": "esriSLS",
                                            "style": "esriSLSSolid"
                                        },
                                        "type": "esriSFS",
                                        "style": "esriSFSSolid"
                                    },
                                    "label": "4",
                                    "classMaxValue": 4
                                }]
        web_map.add_layer(gis.content.get(views_dict[key]),
                        {"type": "FeatureLayer",
                        "renderer": map_renderer,
                        "field_name":key,
                        "minValue":1})
    
    # save the map
    web_map_properties = {'title':web_map_title,
                        'snippet':web_map_snippet,
                        'tags':web_map_tags}

    web_map_item = web_map.save(item_properties=web_map_properties)


    # get json data of the web map
    map_search = gis.content.search(web_map_title)
    map_item = map_search[0]
    map_json = map_item.get_data()

    # set visibility to false
    for layer in map_json['operationalLayers']:
        layer['visibility'] = False 

    # update the json file of the web map 
    item_properties = {"text": json.dumps(map_json)}
    item = gis.content.get(map_item.id)
    item.update(item_properties=item_properties)

    return web_map_item

def recur_dictify(frame):
    # create the dict strcutre of layer groups
    d = collections.OrderedDict()
    if len(frame.columns) == 1:
        if frame.values.size == 1: return frame.values[0][0]
        return frame.values.squeeze()
    grouped = frame.groupby(frame.columns[0], sort=False)
    for k,g in grouped:
        d[k] = recur_dictify(g.ix[:,1:]) 
    return d

def create_group(dict_strcture, template_group_json):
    # create layer groups and set the visibility 
    
    # copy local template
    base_json = copy.deepcopy(template_group_json)
    
    # rename the group
    base_json['label'] = list(dict_strcture.keys())[0]
    base_json['id'] = list(dict_strcture.keys())[0] 
    
    layer_list_json_group = []
    for layer_list_index, layer_list in enumerate(dict_strcture[list(dict_strcture.keys())[0]].keys()):
        # create local copy of the layer list json
        local_layer_list_json = copy.deepcopy(template_widget_json)
        
        # set label of layer _list
        local_layer_list_json['label'] = layer_list
        
        # set id of layer list 
        local_layer_list_json['id'] = 'widgets_LayerList_Widget_' + str(list(dict_strcture.keys())[0]) + '_' + str(layer_list_index)
        
        # get the list of layers to show
        try: 
            subgroup_list = [map_layer_dict[x] for x in dict_strcture[list(dict_strcture.keys())[0]][layer_list]]

            # set the visibility according to the dict
            for lyr in local_layer_list_json['config']['layerOptions']:
                if lyr in subgroup_list:
                    local_layer_list_json['config']['layerOptions'][lyr]['display'] = True
                else: 
                    local_layer_list_json['config']['layerOptions'][lyr]['display'] = False
        except:
            pass

        # add layer group to local list
        layer_list_json_group.append(local_layer_list_json)
    
    # set the base widgets to the local list of groups
    base_json['widgets'] = layer_list_json_group
                 
    return base_json 


def create_layer_groups():
    # create groups of the layers to display them in separate layer lists
    # read csv file of the col hierarchy
    df = pd.read_csv(csv_file_location)

    # filter to the cols where views are required 
    df = df[['Group', 'SubGroup', 'New_Code', 'Order']][df['has_view'] == 'yes']

    # sort according to the provided order of the col\
    #  as this order will be the same when adding the views to the map
    df = df.sort_values(by='Order',ascending=False)

    # create the layer dict structure
    layer_strcture = recur_dictify(df)

    print_text_log(layer_strcture)

    # get local ids of the views within the map  
    map_search = gis.content.search(web_map_title)
    map_item = map_search[0]
    map_json = map_item.get_data()
    map_layer_dict = {}
    for lyr in map_json['operationalLayers']:
        if lyr['popupInfo']['fieldInfos'][2]['fieldName'] == 'WardCODE':
            map_layer_dict[lyr['layerDefinition']['drawingInfo']['renderer']['field']+ '_ward'] = lyr['id']
        elif lyr['popupInfo']['fieldInfos'][1]['fieldName'] == 'BoroughCOD':
            map_layer_dict[lyr['layerDefinition']['drawingInfo']['renderer']['field']+ '_borough'] = lyr['id']
        else:
            print_text_log('layer_error')
            print_text_log(lyr['layerDefinition']['drawingInfo']['renderer']['field'])
            print_text_log(lyr['popupInfo']['fieldInfos'][2]['fieldName'])
    print_text_log(map_layer_dict)

    # get the json file from the app 
    app_search = gis.content.search(web_app_title)
    app_item = app_search[0]
    app_json = app_item.get_data()

    # copy the widget group json section
    groups_json =  copy.deepcopy(app_json['widgetPool']['groups'])

    # copy the widget group json section
    template_group_json = copy.deepcopy(groups_json[0])

    # copy the widget json section
    template_widget_json = copy.deepcopy(template_group_json['widgets'][0])

    # create layer groups 
    app_json['widgetPool']['groups'] = [create_group(layer_strcture, template_widget_json)]

    # set the "Keeps map extent and layers visibility while leaving the app." to false
    app_json['keepAppState'] = False

    # update web app json file
    item_properties = {"text": json.dumps(app_json)}
    item = gis.content.get(app_item.id)
    item.update(item_properties=item_properties)

    return "Done!"

def update_func(lyr, target_feature):
    # func to try the update again after 5 seconds if it fails 
    try:
        logger.debug(lyr)
        logger.debug(type(lyr))
        lyr.layers[0].edit_features(updates = [target_feature]) 
    except RuntimeError:
        print_text_log('Secondary connection error')
        time.sleep(5)
        update_func(lyr, target_feature)


def make_json(shp_file):
    # convert shpfile to Geojson
    gpd.read_file(shp_file).to_file(shp_file[:-4]+".geojson", driver='GeoJSON')
    print_text_log(f"file {shp_file} was converted to geojson")
    return(shp_file[:-4]+".geojson")

def get_data_from_json(json_file):
    # open Geojson 
    json_object = open(json_file, 'r')
    json_data = json.load(json_object)
    logger.debug(f"Geojson file read")
    json_object.close()
    return json_data

def update_geometry(json_data,lyr,id_col= 'Identifier'):
    # take geometry in Geojson form and convert it to features and update
    print_text_log(f"Updating geometry using column {id_col} for ID")
    for index, item in enumerate(json_data['features']):
        condition = f"{id_col} = '{item['properties'][id_col]}'"
        logger.debug (f"selection condition is {condition}")

        target_feature = deepcopy(lyr.layers[0].query(where = condition).features[0])
        target_feature.geometry['rings'] = item['geometry']['coordinates']
        
        try: 
            update_func(lyr, target_feature)
        except RuntimeError:
            print_text_log('Primary connection error')
            time.sleep(5)
            update_func(lyr, target_feature)

        print_text_log(f"feature {item['properties'][id_col]}, {index+1} out of {len(json_data['features'])} was updated")


def find_extra_fields(lyr, df):
    # find the extra fields which are added to the feature
    field_list = []
    for field in lyr.layers[0].manager.properties.fields:
        field_list.append(field['name'])
    df_fields = set(df.keys())

    new_fields_list = df_fields.difference(set(field_list))
    
    
    new_fields_list = [x for x in new_fields_list if x.lower() not in ['shape_area', 'shape_length', 'date_unix']]
    if len(new_fields_list) == 0: 
        return 0
    print_text_log(f"New columns found are {str(new_fields_list)}")
    new_fields_type_dict = {}
    for new_field in new_fields_list:
        new_fields_type_dict[new_field] = df[new_field].dtypes
    
    return new_fields_type_dict


def make_new_field(new_fields_type_dict):
    # create the dictionary required for the new fields 
    new_field_list = []
    string_template = {
            "name": "name",
            "type": "esriFieldTypeString",
            "alias": "alias",
            "sqlType": "sqlTypeOther",
            "length": 800,
            "nullable": True,
            "editable": True,
            "visible": True,
            "domain": None,
            "defaultValue": None
            }
    numerical_template = {
            "name": "name",
            "type": "esriFieldTypeDouble",
            "alias": "alias",
            "sqlType": "sqlTypeOther",
            "nullable": True,
            "editable": True,
            "visible": True,
            "domain": None,
            "defaultValue": None
            }
    for field_name, field_type in new_fields_type_dict.items():
        if field_type == 'O':
            field_template = deepcopy(string_template)
            field_template["name"] = field_name
            field_template["alias"] = field_name
            new_field_list.append(field_template)
        elif field_type in ['int64', 'float64', 'int32', 'float32']:
            field_template = deepcopy(numerical_template)
            field_template["name"] = field_name
            field_template["alias"] = field_name
            new_field_list.append(field_template)
    return new_field_list


def add_fields(lyr, new_field_list):
    # add now fields to the feature
    logger.debug(new_field_list)
    lyr.layers[0].manager.add_to_definition({'fields':new_field_list})


def find_feature(search_text):
    # take a string and return the related layer
    
    layer_search = gis.content.search(search_text, item_type="Feature Layer Collection")

    if len(layer_search) < 1:
        print_text_log ('Search Empty!')
        raise Exception ('Search Empty!')

    print_text_log(f"{len(layer_search)} layers were found. Selecting the first one")
    
    found_names =[]
    for item in layer_search:
        found_names.append('{}; {}; {}'.format(str(item.title), str(item.type), str(item.id)))
    logger.debug(str(found_names))

    lyr = FeatureLayerCollection.fromitem(layer_search[0])
    return lyr

def read_update_csv(csv_file):
    # read csv file and 
    csv_df = pd.read_csv(csv_file)
    csv_df['DATE_UNIX'] = pd.to_datetime(csv_df['Survey_Dat']).astype('int64')//10**9
    return csv_df

def update_new_survey(lyr, csv_df, id_col = 'Identifier', list_of_update_col = ['FASCIA', 'ACTIVITY', 'USE_CLASS']):
    # update row if survey is more recent than last edit
    print_text_log(f"Updating columns {str(list_of_update_col)}, and using column {id_col} for ID")
    update_count, skip_count = 0, 0
    for index, row in csv_df.iterrows():
        condition = f"{id_col} = '{row[id_col]}'"
        logger.debug (f"selection condition is {condition}")
        target_feature = deepcopy(lyr.layers[0].query(where = condition).features[0])
        if target_feature.attributes['EditDate'] < row['DATE_UNIX']:
            for update_col in list_of_update_col:
                target_feature.attributes[update_col] = row[update_col]

            try: 
                update_func(lyr, target_feature)
            except RuntimeError:
                print_text_log('Primary connection error')
                time.sleep(5)
                update_func(lyr, target_feature)


            print_text_log(f"Feature {row[id_col]}, {index+1} out of {csv_df.shape[0]} is updated")
            update_count += 1
        else: 
            print_text_log(f"Feature {row[id_col]}, {index+1} out of {csv_df.shape[0]} is skipped")
            skip_count += 1
    
    print_text_log(f"{update_count} features updated, and {skip_count} features skipped out of {csv_df.shape[0]} features")


def update_all(lyr, csv_df, id_col = 'Identifier', list_of_update_col = ['Name', 'Class', 'activity']):
    # update all rows disregarding the survey
    print_text_log(f"Updating columns {str(list_of_update_col)}, and using column {id_col} for ID")
    for index, row in csv_df.iterrows():
        condition = f"{id_col} = '{row[id_col]}'"
        logger.debug (f"selection condition is {condition}")
        target_feature = deepcopy(lyr.layers[0].query(where = condition).features[0])
        

        for update_col in list_of_update_col:
            target_feature.attributes[update_col] = row[update_col]

        
        try: 
            update_func(lyr, target_feature)
        except RuntimeError:
            print_text_log('Primary connection error')
            time.sleep(5)
            update_func(lyr, target_feature)


        print_text_log(f"Feature {row[id_col]}, {index+1} out of {csv_df.shape[0]} is updated")
    print_text_log("Update completed!")

##