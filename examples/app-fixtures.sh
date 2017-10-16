#!/bin/sh

# quit on errors:
set -o errexit

# quit on unbound symbols:
set -o nounset

DIR=`dirname "$0"`

cd $DIR
export FLASK_APP=app.py

# Create the user
flask users create -a info@inveniosoftware.org --password 123456

# Upload sample records
echo '{"title": "Public", "body": "test 1", "public": 1}' | flask index put \
    demo-default-v1.0.0 example
echo '{"title": "Private", "body": "test 2", "public": 0}' | flask index put \
    demo-default-v1.0.0 example
