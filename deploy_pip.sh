#!/bin/sh
rm -rf dist/ || true
python3 setup.py sdist bdist_wheel
python -m twine upload -c .pypirc --repository dataflows_airtable --verbose dist/*
