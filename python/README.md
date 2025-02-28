# Python Client For AMG8833 Thermal Camera on Raspberry Pi

# Introduction

This code is adapted from the code by [Joshua Hrisko](https://github.com/josh-hrisko) at https://github.com/makerportal/AMG8833_IR_cam

The original code retrieves data from the AMG8833 thermal camera across the I2C bus before using interpolation to display it at higher resolutions. This code reads the data from an API implemented in the [sensor-api-server](https://github.com/big-jr/sensor-api-server) repo.

The code now has a Poetry configuration, and I've made a few changes to use the latest (at the moment) versions of the `numpy`, `matplotlib` and `scipy` packages.

Don't run this code on the Raspberry Pi - although it WILL work, it won't be fast and it will still be looking for the Raspberry Pi running the server code. This code has been tested on both Windows and Linux, just create the virtual environment on a client machine and run it there.

# Command Line

Run the script with:

```bash
python -s main.py -h
```

to get the arguments for the script.
