from PIL import Image

from js import document, console, Uint8Array, window, File #type: ignore
from pyodide import create_proxy #type: ignore
from pyodide.http import pyfetch #type: ignore
import asyncio
import io
import numpy as np
from functools import partial
# all 'paths' loads in py-env are in flat file structure:
# from utils.investigate_autopopulate import get_function_arg_info
from investigate_autopopulate import get_all_skimage_modules, get_child_functions, get_function_arg_info #type: ignore

from skimage.transform import swirl, PiecewiseAffineTransform, warp
from skimage.filters import butterworth

current_emoji = "🦴"
current_filter_name = None #populated at end of loading

emoji_data: dict[str, np.array] = {}

def swirl_filter(my_array: np.array) -> np.array:
    return swirl(my_array, rotation = 0, strength = 15, radius = 300)

def affine_filter(my_array: np.array) -> np.array:
    rows, cols = my_array.shape[0], my_array.shape[1]

    src_cols = np.linspace(0, cols, 20)
    src_rows = np.linspace(0, rows, 10)
    src_rows, src_cols = np.meshgrid(src_rows, src_cols)
    src = np.dstack([src_cols.flat, src_rows.flat])[0]

    # add sinusoidal oscillation to row coordinates
    dst_rows = src[:, 1] - np.sin(np.linspace(0, 3 * np.pi, src.shape[0])) * 50
    dst_cols = src[:, 0]
    dst_rows *= 1.5
    dst_rows -= 1.5 * 50
    dst = np.vstack([dst_cols, dst_rows]).T


    tform = PiecewiseAffineTransform()
    tform.estimate(src, dst)

    out_rows = my_array.shape[0] - 1.5 * 50
    out_cols = cols
    return warp(my_array, tform, output_shape=(out_rows, out_cols))

def butterworth_filter(my_array: np.array, frequency = 0.1, high_pass=False, order=8.0) -> np.array:
    return butterworth(my_array, frequency, high_pass=high_pass, order=order)

filter_names_manual = {
    "swirl": swirl_filter,
    "affine": affine_filter,
    "butterworth_low": partial(butterworth_filter, high_pass=False, order=8.0),
    "butterworth_high": partial(butterworth_filter, frequency = 0.01, high_pass=True, order=8.0)
}

#filter_names = filter_names_manual

auto_filters = {}

def get_all_viable_filters() -> dict:
    result = {}
    for module in get_all_skimage_modules():
        for function in get_child_functions(module):
            req, opt = get_function_arg_info(function)
            if len(req) == 1 and req[0].name.lower() == 'image':
                result[function.__name__] = {"func" : function, "module": module}

    console.log(f"Aded {len(result)} viable filters with one required argument called 'image'")
    return result

def populate_filters(filter_dict:dict, selector_id = "filter-selector") -> None:
    selector = document.getElementById(selector_id)
    global current_filter_name

    #get list of all modules with viable functions
    for module_name in {filter_dict[func]["module"].__name__ for func in filter_dict}:
        optgroup = document.createElement("optgroup")
        optgroup.label = module_name
        for module_function in [func for func in filter_dict if filter_dict[func]["module"].__name__ == module_name]:
            if current_filter_name is None: 
                current_filter_name = module_function
            option = document.createElement("option")
            option.innerText = module_function
            option.value = module_function
            optgroup.appendChild(option)
            auto_filters[module_function] = filter_dict[module_function]["func"]
        selector.appendChild(optgroup)

populate_filters(get_all_viable_filters())
console.log(str(auto_filters))

filter_names = auto_filters

async def get_emoji_bytes(url: str):
    response = await pyfetch(url)
    if response.status == 200:
        return await response.bytes()

async def _select_emoji_and_display(e):
    global current_emoji
    current_emoji = e.target.value
    await _fetch_and_display()

async def _select_filter_and_display(e):
    global current_filter_name
    current_filter_name = e.target.value
    await _fetch_and_display()

async def _fetch_emoji_data(emoji_name: str) -> np.array:
    emoji_code = "-".join(f"{ord(c):x}" for c in emoji_name).upper()
    url = f"https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/618x618/{emoji_code}.png"
    console.log(f"Getting emoji {emoji_name} with value {emoji_code} at url {url}")


    #BytesIO wants a bytes-like object, so convert to bytearray first
    bytes_list = bytearray(await get_emoji_bytes(url))
    my_bytes = io.BytesIO(bytes_list) 

    #Create PIL image from BytesIO 
    my_image = Image.open(my_bytes)

    #Convert to an np-array to allow for processing
    return np.array(my_image.convert()) # convert() is key, as these images use a pallete!!

async def _emoji_data(emoji_name: str) -> np.array:
    if emoji_name not in emoji_data:
        emoji_data[emoji_name] = await _fetch_emoji_data(emoji_name)
    
    return emoji_data[emoji_name]

def array_to_image(data:np.array) -> Image:
    if data[row:= 0][column:= 0][red:= 0] < .99:
        # Many transforms represent RGB as floats in the range 0-1, which pillow does not like
        # This converts their values back to 0-255
        return Image.fromarray((data*255).astype(np.uint8)) 
    else:
        return Image.fromarray(data.astype(np.uint8))

async def _fetch_and_display():
    # Get an emoji image from cache or fetch from web
    emoji_data = await _emoji_data(current_emoji)

    #Image Processing
    my_array = filter_names[current_filter_name](emoji_data)

    #convert back to Pillow image:
    my_image = array_to_image(my_array)

    #Export image from Pillow as bytes to get to Javascript
    my_processed_stream = io.BytesIO()
    my_image.save(my_processed_stream, format="PNG")
    processed_image_file = File.new([Uint8Array.new(my_processed_stream.getvalue())], "new_image_file.png", {type: "image/png"})

    #Export image from 
    my_original_stream = io.BytesIO()
    original_data = await _emoji_data(current_emoji)
    original_image = array_to_image(emoji_data)
    original_image.save(my_original_stream, format="PNG")
    original_image_file = File.new([Uint8Array.new(my_original_stream.getvalue())], "new_image_file.png", {type: "image/png"})

    #remove all children from divs:
    remove_all_children("new_image")
    remove_all_children("original_image")

    #Create new tags and insert into page
    new_image = document.createElement('img')
    new_image.src = window.URL.createObjectURL(processed_image_file)
    document.getElementById("new_image").appendChild(new_image)

    original_image = document.createElement('img')
    original_image.classList.add("w-auto")
    original_image.src = window.URL.createObjectURL(original_image_file)
    document.getElementById("original_image").appendChild(original_image)

select_emoji_and_display = create_proxy( _select_emoji_and_display)
document.getElementById("emoji-selector").addEventListener("change",  select_emoji_and_display)

select_filter_and_display = create_proxy( _select_filter_and_display)
document.getElementById("filter-selector").addEventListener("change",  select_filter_and_display)

def remove_all_children(parent_id: str):
    parent = document.getElementById(parent_id)

    while parent.firstChild is not None:
        parent.removeChild(parent.firstChild)

await _fetch_and_display()

x=1 #Prevents an apparent error of Pyscript trying to write its final value to the DOM