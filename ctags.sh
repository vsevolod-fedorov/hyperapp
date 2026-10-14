#!/bin/sh

cd $(dirname $0)

# Python sources.
find -name '*.py' | etags -o TAGS -

# Resource definitions and types, tagged by bare name and by full ref.
/usr/bin/python3 scripts/resource_tags.py . >> TAGS
