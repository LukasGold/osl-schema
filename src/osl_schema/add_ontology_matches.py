import os
import json
from pathlib import Path
from rdflib import Graph
import requests
import logging

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)

from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")

from osw.defaults import params as default_params  # noqa: E402
from osw.defaults import paths as default_paths  # noqa: E402

default_params.wiki_domain = os.getenv("OSL_DOMAIN")
default_paths.cred_filepath = os.getenv("OSL_CRED_FP")

from osw.express import OswExpress
from osw.model.entity import Electrode, ActiveMaterial


### main script starts here

osw_obj = OswExpress(
    domain=default_params.wiki_domain, cred_filepath=default_paths.cred_filepath
)

# Use requests to get the turtle file from
# https://raw.githubusercontent.com/emmo-repo/domain-electrochemistry/master/electrochemistry-inferred.ttl
turtle_url = "https://raw.githubusercontent.com/emmo-repo/domain-electrochemistry/master/electrochemistry-inferred.ttl"
response = requests.get(turtle_url)
turtle_data = response.text

# Open the turtle file and parse it with rdflib
g = Graph()
g.parse(data=turtle_data, format="turtle")

# Prefix für rdfs und skos hinzufügen, damit SPARQL-Abfragen funktionieren
g.bind("rdfs", "http://www.w3.org/2000/01/rdf-schema#")
g.bind("skos", "http://www.w3.org/2004/02/skos/core#")

# Define the data directory
data_dir = Path(__file__).parents[2] / "data"


with open(data_dir / "mapping_battinfo_to_osl.json", "r") as f:
    data = json.load(f)

# Load all entities of type Electrode and ActiveMaterial
# whose title is in the keys of the data dictionary
result = osw_obj.load_entity(
    osw_obj.LoadEntityParam(
        titles=[key for key in data.keys()],
    )
)
entities: list[Electrode | ActiveMaterial] = result.entities  # type: ignore

# For each entity check if its iri is in the keys of the data dictionary
# If it is, set its exact_ontology_match to the value of the data dictionary
# Then use rdflib to query the graph and look for an entry with an iri that
# matches the ontology match, and get its rdfs:label to ensure we are getting
# the correct match
for entity in entities:
    fpt = entity.get_iri()
    if fpt in data:
        entity.exact_ontology_match = {data[fpt]}
        print(f"Found an ontology match for {fpt} with label {entity.label[0].text}")
        # SPARQL-Abfrage für skos:prefLabel und skos:altLabel
        query = f"""
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        SELECT ?prefLabel ?altLabel WHERE {{
            <{data[fpt]}> skos:prefLabel ?prefLabel .
            OPTIONAL {{ <{data[fpt]}> skos:altLabel ?altLabel . }}
        }}
        """
        qres = g.query(query)
        # Wenn mehrere Ergebnisse, Fehler werfen
        if len(qres) > 1:
            _logger.warning(f"More than one result for {data[fpt]}")
        # Wenn ein Ergebnis, Labels ausgeben
        for row in qres:
            entity.name = str(row.prefLabel)
            alt_label = str(row.altLabel) if row.altLabel else None
            print(f"Found prefLabel {entity.name} and altLabel {alt_label} for {data[fpt]}")


osw_obj.store_entity(
    osw_obj.StoreEntityParam(
        entities=entities,
        summary="Added ontology matches from EMMO electrochemistry ontology",
        bot=True,
        overwrite=True,
    )
)
