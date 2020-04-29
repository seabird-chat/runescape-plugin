#!/bin/bash

python3 -m grpc_tools.protoc -I./proto --python_out=runescape-plugin --grpc_python_out=runescape-plugin ./proto/seabird.proto
