#!/bin/bash
rm -rf results
rm result*.tar.gz
git checkout -- test_config.py
git checkout -- config.py
git checkout -- run_all_cluster_aws.sh
rm experiments/*
