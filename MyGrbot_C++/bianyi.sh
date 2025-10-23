#!/bin/bash

# cd $PWD/build

sudo rm -rf $PWD/build/*

cd $PWD/build

cmake ..

make -j4

cd ..