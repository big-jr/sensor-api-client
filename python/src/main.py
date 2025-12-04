#######################################################
# Thermal camera Plotter with AMG8833 Infrared Array
# --- with interpolation routines for smoothing image
#
# Original code:
# by Joshua Hrisko
#    Copyright 2021 | Maker Portal LLC
#
# Updates to read from an API:
# Jason Ross, Copyright 2025
#
#######################################################
#
import argparse
import sys
import time
from collections import deque

sys.path.append("../")
import statistics

import matplotlib.pyplot as plt
import numpy as np
import requests
from scipy import interpolate


def check_one_or_more(value):
    """
    Parameter validation for frames
    :param value:
    :return:
    """
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError(f"{value} is invalid - it must be at least 1")

    return result


# Command Line parameters
parser = argparse.ArgumentParser("Client for the sensor-api-server")
parser.add_argument(
    "server", type=str, help="Full domain name or API of the server hosting the API"
)
parser.add_argument(
    "--agc",
    action="store_true",
    default=False,
    help="Whether to implement Automatic Gain Control on the image, to adjust the temperature range. Default is not to.",
)
parser.add_argument(
    "--frames",
    type=check_one_or_more,
    help="The number of frames to display. Default is to run until stopped explicitly.",
)
parser.add_argument(
    "--timing",
    action="store_true",
    default=False,
    help="Whether to display the average frame times. Default is not to.",
)

args = parser.parse_args()

print(f"Server: {args.server}")

SENSOR_API_URL = f"http://{args.server}:8000/sensor/0/data"

#####################################
# Interpolation Properties
#####################################
#
# original resolution
pix_res = (8, 8)  # pixel resolution
xx, yy = (
    np.linspace(0, pix_res[0], pix_res[0]),
    np.linspace(0, pix_res[1], pix_res[1]),
)
zz = np.zeros(pix_res)  # set array with zeros first
# new resolution
pix_mult = 6  # multiplier for interpolation
interp_res = (int(pix_mult * pix_res[0]), int(pix_mult * pix_res[1]))
grid_x, grid_y = (
    np.linspace(0, pix_res[0], interp_res[0]),
    np.linspace(0, pix_res[1], interp_res[1]),
)


# interp function
def interp(z_var):
    # cubic interpolation on the image
    # at a resolution of (pix_mult*8 x pix_mult*8)
    f = interpolate.RectBivariateSpline(xx, yy, z_var)
    return f(grid_x, grid_y)


grid_z = interp(zz)  # interpolated image
#
#####################################
# Start and Format Figure
#####################################
#
plt.rcParams.update({"font.size": 16})
fig_dims = (10, 9)  # figure size
fig, ax = plt.subplots(figsize=fig_dims)  # start figure
fig.canvas.manager.set_window_title("AMG8833 Image Interpolation")
im1 = ax.imshow(
    grid_z, vmin=18, vmax=27, cmap=plt.cm.RdBu_r
)  # plot image, with temperature bounds
cbar = fig.colorbar(im1, fraction=0.0475, pad=0.03)  # colorbar
cbar.set_label("Temperature [C]", labelpad=10)  # temp. label
fig.canvas.draw()  # draw figure

ax_bgnd = fig.canvas.copy_from_bbox(ax.bbox)  # background for speeding up runs
fig.show()  # show figure
#
#####################################
# Plot AMG8833 temps in real-time
#####################################
#

request_times = []
parse_times = []
read_times = []
interp_times = []
draw_times = []
errors = 0

AGC_TIME = 2.0  # 2 seconds between gain adjustments
AGC_SAMPLE_COUNT = 10 # Average frames

last_agc_adjustment = time.perf_counter()

agc_min_temps = deque()
agc_max_temps = deque()

# Unlimited frames is implemented as just a huge number for the moment
for frame_count in range(0, args.frames or 1000000000):
    read_start_time = time.perf_counter()

    # Hard-coded URL depends on server - ideally change this to dynamic
    request = requests.get(SENSOR_API_URL, timeout=5)

    request_end_time = time.perf_counter()
    request_times.append(request_end_time - read_start_time)

    data = request.json()

    parse_times.append(time.perf_counter() - request_end_time)

    if data.get("error", True):  # if error in pixel, re-enter loop and try again
        errors += 1
        continue

    pixels = data["temperatures"]  # read pixels with status
    T_thermistor = data.get("ambient_temperature", 0)  # read thermistor temp
    read_end_time = time.perf_counter()

    fig.canvas.restore_region(ax_bgnd)  # restore background (speeds up run)
    new_z = interp(np.reshape(pixels, pix_res))  # interpolated image

    interp_end_time = time.perf_counter()

    im1.set_data(new_z)  # update plot with new interpolated temps
    ax.draw_artist(im1)  # draw image again
    fig.canvas.blit(ax.bbox)  # blitting - for speeding up run
    fig.canvas.flush_events()  # for real-time plot
    draw_end_time = time.perf_counter()

    read_times.append(read_end_time - read_start_time)
    interp_times.append(interp_end_time - read_end_time)
    draw_times.append(draw_end_time - interp_end_time)

    if len(agc_min_temps) == AGC_SAMPLE_COUNT:
        agc_min_temps.popleft()
    agc_min_temps.append(min(pixels))

    if len(agc_max_temps) == AGC_SAMPLE_COUNT:
        agc_max_temps.popleft()
    agc_max_temps.append(max(pixels))

    if not time.perf_counter() - last_agc_adjustment >= AGC_TIME:
        min_temp_limit = min(agc_min_temps) - 1
        max_temp_limit = max(agc_max_temps) + 1

        im1.set_clim(min_temp_limit, max_temp_limit)
        fig.canvas.draw()
        last_agc_adjustment  =time.perf_counter()

if args.timing:
    print(f"Request: {(statistics.mean(request_times) * 1000):.2f}ms")
    print(f"Parse:   {(statistics.mean(parse_times) * 1000):.2f}ms")
    print(f"Read:    {(statistics.mean(read_times) * 1000):.2f}ms")
    print(f"Interp:  {(statistics.mean(interp_times) * 1000):.2f}ms")
    print(f"Draw:    {(statistics.mean(draw_times) * 1000):.2f}ms")
    print(f"Errors:  {errors}")
