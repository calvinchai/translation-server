import yaml
import os
import requests
from bs4 import BeautifulSoup as bs

"""
The content on the main page will be stored in root.yaml
other will store in the path.yaml
before proceeding, make sure that the parent path is created, if not, create it
create dict for parent path first
for word that exists in parent dict, comment it out and place to the end of the yaml file
for word that does not exist in parent dict, add it to the end of the yaml file
if the word does not exist in translation dict, add it

"""


class PageTranslation:
    pass
