import inspect
from typing import List
import skimage
from dataclasses import dataclass
from pprint import pprint, pp


def main() -> None:
    #Print a list of all available functions
    #print_all_functions_from_all_modules()

    #print function argument info for all functions within a submodule
    #print_module_function_info_signature(skimage.transform)

    #print function summary for all functions in a submodule
    #print_module_function_summary(skimage.transform)

    #Or print function summaries for ALL modules (long):
    for m in get_all_skimage_modules():
        print_module_function_summary(m)
        print("\n------\n")

    #Print number of member functions for all modules, with how many require a single argument and how many require more than one (with no default)
    #print_all_module_summary()


def get_child_functions(m:object) -> List:
    return [member for _, member in inspect.getmembers(m) if inspect.isfunction(member)]

def get_child_modules(m:object) -> List:
    return [member for _, member in inspect.getmembers(m) if inspect.ismodule(member)]

def get_all_skimage_modules() -> List:
    return [member for _, member in inspect.getmembers(skimage) if inspect.ismodule(member)]

#Prints detailed info of the functions for a single module, along with their argument types and default, if any
def print_module_function_info(m:object) -> None:
    print(f"--- Info for module {m.__name__} ---")
    for f in get_child_functions(m):
        print(f"--- Function {f.__name__} ---")
        required_args, optional_args = get_function_arg_info(f)

        for data in required_args:
            req, param = data
            print(f"\t{req:<20}{param.kind:<25}REQUIRED")

        for data in optional_args:
            opt, param = data
            print(f"\t{opt:<20}{param.kind:<25}{str(param.default):<25}{str(param.kind):<30}")

#Print short info about all the functions in a module, including which functions have more than 1 required argument and the names of those arguments
def print_module_function_summary(m:object) -> None:
    functions_with_one_req = []
    functions_more_req = []

    for f in get_child_functions(m):
        required_args, optional_args = get_function_arg_info(f)
        if len(required_args) > 1:
            functions_more_req.append(f)
        else:
            functions_with_one_req.append(f)

    print(f"Module {m.__name__} has {len(get_child_functions(m))} member functions")
    print(f"{len(functions_with_one_req)} functions with only one required argument")
    #print(f"\t{', '.join([f.__name__ for f in functions_with_one_req])}")
    pprint([f.__name__ for f in functions_with_one_req], compact=True, indent=2)
    print(f"{len(functions_more_req)} requiring more than one:")
    pprint([f.__name__ for f in functions_more_req], compact=True, indent=2)
    print("")
    

    for f in functions_more_req:
        print(f"Function {f.__name__:<25} requires {', '.join([str(arg) for arg in get_function_arg_info(f)[0]])}")

#Print the list of all modules in skimage, how many member functions they have, how many of those
#have one required argument and how many have more than one
def print_all_module_summary() -> None:
    txt = "{name:<25}{functions:^18}{one_req:^30}{more_req:^25}"
    print(txt.format(name="Module", functions="Total Functions", one_req="One Required Argument", more_req="More Than One Required Argument"))
    total_functions = total_one = total_more = 0
    for module in get_all_skimage_modules():
        functions_with_one_req = []
        functions_more_req = []

        for f in get_child_functions(module):
            required_args, optional_args = get_function_arg_info(f)
            if len(required_args) > 1:
                functions_more_req.append(f)
            else:
                functions_with_one_req.append(f)

        total_functions += len(get_child_functions(module))
        total_one += len(functions_with_one_req)
        total_more += len(functions_more_req)
        
        print(txt.format(name=module.__name__, functions=len(get_child_functions(module)), one_req=len(functions_with_one_req), more_req=len(functions_more_req)))
    print(txt.format(name="TOTAL", functions=total_functions, one_req=total_one, more_req=total_more))

#Returns a tuple of two list - the first is the required arguments for the given function, the second is the optional arguments
def get_function_arg_info(f:object) -> tuple:
    sig = inspect.signature(f)
    required_args = [param for _, param in sig.parameters.items() if param.default == inspect._empty and param.kind != inspect.Parameter.VAR_KEYWORD]
    optional_args = [param for _, param in sig.parameters.items() if param not in required_args]
    return required_args, optional_args

#Print a brief list of all functions in each module of skimage
def print_all_functions_from_all_modules():
    for module in get_all_skimage_modules():
        print(f"--- Functions from module {module.__name__} ---")
        functions = get_child_functions(module)

        pprint([f.__name__ for f in functions], compact=True)
        print("")

if __name__ == "__main__":
    main()