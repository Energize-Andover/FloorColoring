from file_conversion_tools import *
from pdf_tools import *
from coordinate_tools import *
from bs4 import BeautifulSoup
from colour import Color
import os
import shutil
import svgwrite
import svgutils.transform as st

# Define global variables
svg_path = None
svg_output_path = None
pdf_path = None
png_path = None
text_and_coords = None
soup = None
view_box = None
media_box = None

red_value = None
green_value = None
blue_value = None

red = Color('#ff0000')
green = Color('#00ff00')
blue = Color('#00bfff')

temperature_colors = None
co2_colors = None


def init(r, g, b):
    global svg_path, svg_output_path, pdf_path, png_path, text_and_coords, soup, view_box, media_box, red_value, green_value, blue_value
    svg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Andover HS level 3.svg")
    svg_output_path = svg_path[0:-4] + "_filled_rooms.svg"
    pdf_path = svg_path[0:-4] + ".pdf"
    png_path = svg_path[0:-4] + ".png"

    if os.path.exists(svg_output_path):
        os.remove(svg_output_path)

    svg_to_pdf(svg_path, pdf_path)
    text_and_coords = get_text_and_coordinates(pdf_path)

    svg_to_png(svg_path, png_path, 72)
    initialize_cv(png_path)

    # Extract the viewBox from the SVG using BeautifulSoup and convert it into a tuple of integers
    soup = BeautifulSoup(open(svg_path), "html.parser")
    view_box = tuple(map(int, soup.find("svg")["viewbox"].split(" ")))
    media_box = get_media_box(pdf_path)

    red_value = r
    green_value = g
    blue_value = b
    generate_color_arrays()


def fill_room(room, color_hex_code, opacity):
    temp_path = svg_path[0:-4] + '_temp_rect.svg'

    if not os.path.exists(svg_output_path):
        shutil.copy(svg_path, svg_output_path)

    room_rect_info = get_room_rect_info(room, media_box, text_and_coords, png_path)

    if room_rect_info is not None:
        room_corner = (room_rect_info[0], room_rect_info[1])
        room_width = room_rect_info[2]
        room_height = room_rect_info[3]

        room_rect_svg_coords = get_svg_coords(room_corner, view_box, media_box)
        room_svg_width = get_svg_measure(room_width, view_box[2], media_box[2])
        room_svg_height = get_svg_measure(room_height, view_box[3], media_box[3])

        dwg = svgwrite.Drawing(temp_path)
        dwg.add(dwg.rect(insert=room_rect_svg_coords, size=(room_svg_width, room_svg_height), fill=color_hex_code,
                         opacity=opacity, id="room-rect-{0}".format(room)))
        dwg.save()  # Save the path to a temporary file

        # Merge the files
        floor_plan = st.fromfile(svg_output_path)
        second_svg = st.fromfile(temp_path)
        floor_plan.append(second_svg)
        floor_plan.save(svg_output_path)
        os.remove(temp_path)


def generate_color_arrays():
    global temperature_colors, co2_colors
    temperature_colors = generate_color_array(red_value[0], green_value[0], blue_value[0])
    co2_colors = generate_color_array(red_value[1], green_value[1], blue_value[1])


def generate_color_array(red_val, green_val, blue_val):
    blue_to_green = list(blue.range_to(green, green_val - blue_val + 1))
    green_to_red = list(green.range_to(red, red_val - green_val))
    green_to_red.pop(0)  # Remove the repeat of green
    return blue_to_green + green_to_red


def get_value_color(value, is_temperature_value):
    value_index = 0 if is_temperature_value else 1
    global array_index
    array_index = 0

    last_element_index = red_value[value_index] - blue_value[value_index] - 1

    if value <= blue_value[value_index]:
        array_index = 0
    elif value < red_value[value_index]:
        array_index = last_element_index - (red_value[value_index] - value) + 1
    else:
        array_index = last_element_index  # The index of the last element in the color array

    return temperature_colors[array_index].hex_l if is_temperature_value else co2_colors[array_index]


def fill_from_data(data, is_temperature_value):
    value = data['temperature'] if is_temperature_value else data['co2']
    color = get_value_color(value, is_temperature_value)
    fill_room(data['room'], color, 0.6)


def add_overlay():
    temp_path = svg_path[0:-4] + '_temp_overlay.svg'
    dwg = svgwrite.Drawing(temp_path)
    dwg.add(dwg.rect(insert=(0, 0), size=(view_box[2], view_box[3]), fill='#ffffff',
                     opacity=0, id="floor-plan-overlay"))
    dwg.save()  # Save the path to a temporary file
    floor_plan = st.fromfile(svg_output_path)
    second_svg = st.fromfile(temp_path)
    floor_plan.append(second_svg)
    floor_plan.save(svg_output_path)
    os.remove(temp_path)
