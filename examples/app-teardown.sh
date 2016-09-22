#!/bin/sh

DIR=`dirname "$0"`

cd $DIR
export FLASK_APP=app.py

# Delete database
flask db drop --yes-i-know

# Delete indices
flask index delete demo --yes-i-know
[ -e "$DIR/public.json" ] && rm $DIR/public.json
[ -e "$DIR/private.json" ] && rm $DIR/private.json
