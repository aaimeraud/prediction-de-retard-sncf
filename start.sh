#!/bin/bash

# SNCF Delay Prediction - Quick Start Launcher

cd "$(dirname "$0")" || exit 1

.venv/bin/python launcher.py
