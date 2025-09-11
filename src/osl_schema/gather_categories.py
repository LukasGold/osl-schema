"""
Module for gathering categories, subcategories, and instances from an OSW MediaWiki instance.

This module provides functions to query categories, subcategories, and instances,
and to format the results as strings for further processing or export.
"""

import os
from pathlib import Path
import logging
import re

_logger = logging.getLogger()
_logger.setLevel(logging.INFO)

from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")
# load_dotenv(Path(r"C:\Users\gold\github\osw-package-maintenance\tools\batteries\.env"))

from osw.defaults import params as default_params  # noqa: E402
from osw.defaults import paths as default_paths  # noqa: E402

default_params.wiki_domain = os.getenv("OSL_DOMAIN")
default_paths.cred_filepath = os.getenv("OSL_CRED_FP")

from osw.express import OswExpress


def query_return_dict_list(
    osw_obj: OswExpress, query: str
) -> list[dict[str, str]]:
    """Executes a MediaWiki ask query and returns the results as a list of dictionaries
    with the keys being the labels assigned to the queried properties.

    Parameters
    ----------
    osw_obj
        The OSW Express object for querying.
    query
        The ask query string.

    Returns
    -------
    list of dict
        List of result dictionaries with 'title' and queried fields.
    """
    matches = re.findall(pattern=r".*?(\|\?[A-Za-z_]*=([A-Za-z_]+))",string=query)
    return_fields = [match[1] for match in matches]
    results = osw_obj.mw_site.ask(query)
    if results is None:
        return list()
    dict_list = list()
    for result in results:
        title: str = result.get("fulltext")
        entry = {"title": title}
        for field in return_fields:
            field_list: list[str] | None = result.get("printouts").get(field)
            if isinstance(field_list, list) and len(field_list) > 0:
                entry[field] = field_list[0]
            else:
                entry[field] = ""
        dict_list.append(entry)
    return dict_list


def get_subcategories(
    osw_obj: OswExpress, category_fpt: str, depth: int = 0, max_depth: int = 5
) -> list[dict[str, str]]:
    """Recursively retrieves subcategories for a given category, always including the queried category itself.

    Parameters
    ----------
    osw_obj
        The OSW Express object for querying.
    category_fpt
        The full page title of the category.
    depth
        Current recursion depth.
    max_depth
        Maximum recursion depth.

    Returns
    -------
    list of dict
        List of dictionaries for the category and its subcategories.
    """
    if depth > max_depth:
        _logger.warning(f"Max depth {max_depth} reached at category {category_fpt}")
        return list()
    query1 = "[[:{category_fpt}]]|?HasName=name".replace(
        "{category_fpt}", category_fpt
    )
    result1 = query_return_dict_list(osw_obj, query1)
    if not result1:
        raise ValueError(f"Category {category_fpt} not found")
    # Always include the queried category itself
    subcategories = [result1[0]]
    query2 = "[[SubClassOf::{category_fpt}]]|?HasName=name".replace(
        "{category_fpt}", category_fpt
    )
    results2 = query_return_dict_list(osw_obj, query2)
    if results2:
        subcategories.extend(results2)
        for result in results2:
            subcat_fpt = result.get("title")
            if subcat_fpt:
                sub_subcategories = get_subcategories(
                    osw_obj=osw_obj,
                    category_fpt=subcat_fpt,
                    depth=depth + 1,
                    max_depth=max_depth,
                )
                subcategories.extend(list(sub_subcategories))

    fpt_list = []
    unique_items = []
    for item in subcategories:
        fpt = item.get("title")
        if fpt and fpt not in fpt_list:
            fpt_list.append(fpt)
            unique_items.append(item)

    return unique_items


def get_subcategories_and_metacategories(
    osw_obj: OswExpress, category_fpt: str, max_depth: int = 5
) -> list[dict[str, str]]:
    """Retrieves subcategories and their meta categories for a given category.

    Parameters
    ----------
    osw_obj
        The OSW Express object for querying.
    category_fpt
        The full page title of the category.
    max_depth
        Maximum recursion depth.

    Returns
    -------
    list of dict
        List of dictionaries for subcategories and their meta categories.
    """
    subcategories = get_subcategories(
        osw_obj=osw_obj,
        category_fpt=category_fpt,
        max_depth=max_depth
    )
    metacategories = list()
    for subcat in subcategories:
        subcat_fpt = subcat.get("title")
        if subcat_fpt:
            metacat_query = "[[-HasMetaCategory::{subcat_fpt}]]|?HasName=name".replace(
                "{subcat_fpt}", subcat_fpt
            )
            metacat_results = query_return_dict_list(osw_obj, metacat_query)
            metacategories.extend(metacat_results)
    all_items = list(subcategories)
    all_items.extend(metacategories)

    return all_items


def get_instances(
    osw_obj: OswExpress, category_fpt: str
) -> list[dict[str, str]]:
    """Retrieves instances of a given category.

    Parameters
    ----------
    osw_obj
        The OSW Express object for querying.
    category_fpt
        The full page title of the category.

    Returns
    -------
    list of dict
        List of dictionaries for the instances.
    """
    query1 = "[[:{category_fpt}]]|?HasName=name".replace(
        "{category_fpt}", category_fpt
    )
    instances = query_return_dict_list(osw_obj, query1)
    query2 = "[[HasSchema::{category_fpt}]]|?HasName=name".replace(
        "{category_fpt}", category_fpt
    )
    instances.extend(query_return_dict_list(osw_obj, query2))
    return instances


def get_all_instances_and_subcategories(
    osw_obj: OswExpress, category_fpt: str, max_depth: int = 5
) -> list[dict[str, str]]:
    """Recursively retrieves all subcategories and their instances for a given category.

    Parameters
    ----------
    osw_obj
        The OSW Express object for querying.
    category_fpt
        The full page title of the category.
    max_depth
        Maximum recursion depth.

    Returns
    -------
    list of dict
        List of dictionaries for all subcategories and instances.
    """
    subcategories = get_subcategories_and_metacategories(
        osw_obj=osw_obj,
        category_fpt=category_fpt,
        max_depth=max_depth
    )
    all_items = list(subcategories)  # start with subcategories
    for subcat in subcategories:
        subcat_fpt = subcat.get("title")
        if subcat_fpt:
            instances = get_instances(
                osw_obj=osw_obj,
                category_fpt=subcat_fpt
            )
            all_items.extend(instances)
    # Remove duplicates based on 'title'
    fpt_list = []
    unique_items = []
    for item in all_items:
        fpt = item.get("title")
        if fpt and fpt not in fpt_list:
            fpt_list.append(fpt)
            unique_items.append(item)
    return unique_items


def append_dict_to_string(
    string: str, dict_list: list[dict[str,str]], note: str
) -> str:
    """Appends a list of dictionaries to a string, formatted with a note.

    Parameters
    ----------
    string
        The base string to append to.
    dict_list
        List of dictionaries to append.
    note
        Note to include in the output.

    Returns
    -------
    str
        The updated string with appended entries.
    """
    string += f"\n# {dict_list[0].get('name')} {note}\n"
    for cat in dict_list:
        string += f'"{cat.get("title")}",  # {cat.get("name")}\n'
    return string


def append_subcategories_to_string(
    string: str, category_fpt: str, osw_obj: OswExpress
) -> str:
    """Appends subcategories of a category to a string.

    Parameters
    ----------
    string
        The base string to append to.
    category_fpt
        The full page title of the category.
    osw_obj
        The OSW Express object for querying.

    Returns
    -------
    str
        The updated string with appended subcategories.
    """
    subcats = get_subcategories_and_metacategories(
        osw_obj=osw_obj,
        category_fpt=category_fpt,
        max_depth=10
    )
    string = append_dict_to_string(
        string,
        subcats,
        ", subcategories and meta categories"
    )
    return string


def append_instances_to_string(
    string: str, category_fpt: str, osw_obj: OswExpress
) -> str:
    """Appends instances of a category to a string.

    Parameters
    ----------
    string
        The base string to append to.
    category_fpt
        The full page title of the category.
    osw_obj
        The OSW Express object for querying.

    Returns
    -------
    str
        The updated string with appended instances.
    """
    instances = get_instances(
        osw_obj=osw_obj,
        category_fpt=category_fpt
    )
    string += f"\n# Instances of {instances[0].get('name')}\n"
    for inst in instances[1:]:
        string += f'"{inst.get("title")}",  # {inst.get("name")}\n'
    return string


def append_subcategories_and_instances_to_string(
    string: str, category_fpt: str, osw_obj: OswExpress
) -> str:
    """
    Appends both subcategories and instances of a category to a string.

    Parameters
    ----------
    string
        The base string to append to.
    category_fpt
        The full page title of the category.
    osw_obj
        The OSW Express object for querying.

    Returns
    -------
    str
        The updated string with appended subcategories and instances.
    """
    string = append_subcategories_to_string(
        string=string,
        category_fpt=category_fpt,
        osw_obj=osw_obj
    )
    string = append_instances_to_string(
        string=string,
        category_fpt=category_fpt,
        osw_obj=osw_obj
    )
    return string


def append_all_subcategories_and_instances_to_string(
    string: str, category_fpt: str, osw_obj: OswExpress
) -> str:
    """Appends all subcategories and instances (recursively) of a category to a string.

    Parameters
    ----------
    string
        The base string to append to.
    category_fpt
        The full page title of the category.
    osw_obj
        The OSW Express object for querying.

    Returns
    -------
    str
        The updated string with all subcategories and instances appended.
    """
    all_items = get_all_instances_and_subcategories(
        osw_obj=osw_obj,
        category_fpt=category_fpt,
        max_depth=10
    )
    string = append_dict_to_string(
        string,
        all_items,
        "and all subcategories and instances"
    )
    return string


if __name__ == '__main__':
    """
    Example usage: Generates a string with categories, subcategories, and instances for several example categories.
    """
    osw_obj_ = OswExpress(
        domain=default_params.wiki_domain, cred_filepath=default_paths.cred_filepath
    )
    string_ = "# This file is auto-generated by gather_categories.py\n"
    # Battery cell materials
    string_ = append_subcategories_to_string(
        string=string_,
        category_fpt="Category:OSWc02165dc24544a10a2046b54506dedac",
        osw_obj=osw_obj_
    )
    # Analytical Laboratory Process
    string_ =append_subcategories_to_string(
        string=string_,
        category_fpt="Category:OSWfa914762adaa4665a63b6a77c3ea6eed",
        osw_obj=osw_obj_
    )
    # Electrochemical testing device
    string_ = append_subcategories_to_string(
        string=string_,
        category_fpt="Category:OSW69729530f3ca4addaf8dd95ea3781607",
        osw_obj=osw_obj_
    )
    string_ += '\n"Item:OSWd8351c3e8e1641c582a5ac5bd0281f9a",  # Maccor Inc.\n'
    # Electrochemical test procedure
    string_ = append_subcategories_to_string(
        string=string_,
        category_fpt="Category:OSWdda41d4a4ec0421babe0295c6edcb5df",
        osw_obj=osw_obj_
    )
    # Electrochemical energy storage device
    string_ = append_subcategories_to_string(
        string=string_,
        category_fpt="Category:OSWbeaf0d4e4dfd4fe29b7349751b3bccba",
        osw_obj=osw_obj_
    )
    # Battery cell format
    string_ = append_all_subcategories_and_instances_to_string(
        string=string_,
        category_fpt="Category:OSWf04e73d3c3cb4e4ea7033066e472e9ff",
        osw_obj=osw_obj_
    )
    # Battery cell form factor
    string_ = append_all_subcategories_and_instances_to_string(
        string=string_,
        category_fpt="Category:OSWc8108cfc369241aba154c4c306497c30",
        osw_obj=osw_obj_
    )
