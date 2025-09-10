from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")

from osw.defaults import params as default_params  # noqa: E402
from osw.defaults import paths as default_paths  # noqa: E402

default_params.wiki_domain = os.getenv("OSL_DOMAIN")
default_paths.cred_filepath = os.getenv("OSL_CRED_FP")

from osw.express import OswExpress, import_with_fallback  # noqa: E402

osw_obj = OswExpress(
    domain=default_params.wiki_domain, cred_filepath=default_paths.cred_filepath
)


DEPENDENCIES = {
    "Electrode": "Category:OSW97c67a6938cd401a8eadcc03bbce9ef1",
    "ActiveMaterial": "Category:OSWd5791d13ae43423ebb97ceb942c62d10",
}

# import_with_fallback(DEPENDENCIES, globals(), osw_express=osw_obj)

osw_obj.fetch_schema(
    osw_obj.FetchSchemaParam(
        schema_title=list(DEPENDENCIES.values()),
        mode="replace",
    )
)
