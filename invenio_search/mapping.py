# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""Elastic Search integration. mapping funtion"""

import json

import os

from jinja2 import Environment, PackageLoader

from invenio.base.globals import cfg


def loadFieldsFromJson(path):
    """extract raw fields from multiples json file"""
    rawfields = {}

    for schemaFile in os.listdir("schemas"):
        jsonSchema = json.loads(open(path + "/" + schemaFile).read())

        try:
            if not isinstance(jsonSchema, dict):
                raise Exception('not a valid schema, not a dictonnary')

            if not jsonSchema.has_key("properties"):
                raise Exception('not a valid schema')

            if not isinstance(jsonSchema['properties'], dict):
                raise Exception('not a valid schema')

            for key, value in jsonSchema['properties'].iteritems():
                rawfields[key] = value

        except Exception:
            print path + "/" + schemaFile + " is not a valid schema"

    return rawfields


def format_fields(rawFields):
    """format fields for es mapping"""
    fields = {}
    for key, value in rawFields.iteritems():
        currentfield = {}

        #if there is subfleid
        if isinstance(value, dict) and value.has_key("items"):
            currentfield["type"] = "object"
            currentfield["properties"] = {}
            for key2, value in value["items"]["properties"].iteritems():
                currentfield["properties"][key2] = {"type":"string"}
        else:
            currentfield["type"] = "string"

        fields[key] = currentfield
    return fields


def dumpsFields(fields):
    """dump fields"""
    dump = ""
    for key, value in fields.iteritems():
        dump = dump + '{% block ' + key + '%}\n'
        dump = dump + '"' + key  + '"' + ":" + json.dumps(value, indent=4, sort_keys=True) + '\n'
        dump = dump + '{% endblock%},\n'
    dump = dump[:-2]
    dump = dump + '\n{% block custom %}\n'
    dump = dump + '{% endblock %}\n'

    return dump


def create_es_mapping():
    """main function, link jinja template and create the mapping"""
    #settings
    jsonInputSchemaFolder = cfg['ES_SCHEMA_FOLDER']
    elasticMappingFile = cfg['ES_MAPPING_FILE']

    generatedFieldFile = "/home/letreguilly/virtualenvs/invenio/src/invenio-search/invenio_search/generated/field.json"
    AnalyserFile = "/home/letreguilly/virtualenvs/invenio/src/invenio-search/invenio_search/base/analyser.json"

    env = Environment(loader=PackageLoader('invenio_search', '.'))

    

    #generate fields
    rawFields = loadFieldsFromJson(jsonInputSchemaFolder)
    formatedfields = format_fields(rawFields)
    dumpsFields(formatedfields)
    
    jsonFields = dumpsFields(formatedfields)
    with open(generatedFieldFile, 'w') as f:
        f.write(jsonFields) 
    
    #render    
    resultJson = env.get_template('base/baseSchema.json').render(
    _all = cfg['ES_TEST'],
    date_detection = cfg['ES_DATE_DETECTION'],
    numeric_detection = cfg['ES_NUMERIC_DETECTION'],
    default_type = cfg['ES_DEFAULT_TYPE'],
    default_analyser = cfg['ES_DEFAULT_ANALYSER']
    )  

    #writing
    with open(elasticMappingFile, 'w') as f:
        f.write(resultJson)
