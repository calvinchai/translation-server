import glob

from flask import Flask
import requests
from bs4 import BeautifulSoup as bs
from bs4 import Comment, Doctype, Script, Stylesheet
import os
import yaml
from config import AppConfig
from flask_cors import CORS
app = Flask(__name__)
# CORS(app)
global_translation_dict = {}


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def reroute(path):
    # Define the target domain to which you want to redirect all requests

    # Redirect the incoming request to the target domain
    abs_path = AppConfig.target_domain + '/' + path
    response = requests.get(abs_path)
    # response.headers.add('Access-Control-Allow-Origin', '*')
    if 'text/html' not in response.headers['Content-Type']:
        return response.content

    # replace href
    soup = bs(response.text, 'html.parser')

    for link in soup.findAll('a'):
        if link['href'].endswith('.pdf'):
            continue
        if link['href'].endswith('.ico'):
            continue
        link['href'] = link['href'].replace(AppConfig.target_domain, AppConfig.local_domain)
    # find all text
    if response.status_code == 404:
        path = '404'
    soup = translate_content(soup, path)
    # replace all japanese to english
    return soup.prettify()


"""
The content on the main page will be stored in root.yaml
other will store in the path.yaml
before proceeding, make sure that the parent path is created, if not, create it
create dict for parent path first
for word that exists in parent dict, comment it out and place to the end of the yaml file
for word that does not exist in parent dict, add it to the end of the yaml file
if the word does not exist in translation dict, add it

"""


def get_dict_path(hierarchy: list, use_alternative=False):
    """
    given a hierarchy, return the path to the yaml file, if hierarchy is empty, return the path to the _root.yaml
    :param use_alternative:
    :param hierarchy: list of path to the current page
    :return: the path to the yaml file
    """
    ext = '.new.yaml' if use_alternative else '.yaml'
    if len(hierarchy) == 0:
        return os.path.join('translation', '_root' + ext)
    return os.path.join('translation', '.'.join(hierarchy) + ext)


def same_level_dict(hierarchy: list):

    files = glob.glob(os.path.join('translation', '.'.join(hierarchy[:-1]), '*.yaml'))
    matched = set()
    for file in files:
        if file.endswith('.new.yaml'):
            continue
        if '.' in file[len(os.path.join('translation', '.'.join(hierarchy[:-1]))):-5]:
            continue
        matched.add(file)
    return matched


def get_all_same_level_dict(hierarchy: list):
    matched = same_level_dict(hierarchy)
    rtn  = []
    for file in matched:
        with open(file, 'r', encoding='utf-8') as f:
            rtn.append(yaml.load(f, Loader=yaml.FullLoader))
    return rtn


def load_dict(hierarchy: list, use_alternative=False):
    """
    given a hierarchy, load the yaml file, if hierarchy is empty, load the _root.yaml
    :param use_alternative:
    :param hierarchy: list of path to the current page
    :return: the dict
    """
    try:
        with open(get_dict_path(hierarchy, use_alternative), 'r', encoding='utf-8') as f:
            return yaml.load(f, Loader=yaml.FullLoader)
    except:
        app.logger.error("Error loading dict for hierarchy: {}".format(hierarchy))
        return {}


def save_dict(hierarchy: list, translation_dict: dict, use_alternative=False):
    """
    given a hierarchy, save the yaml file, if hierarchy is empty, save the _root.yaml
    :param use_alternative:
    :param hierarchy: list of path to the current page
    :param translation_dict: the dict to save
    :return: None
    """
    with open(get_dict_path(hierarchy, use_alternative), 'w', encoding='utf-8') as f:
        yaml.dump(translation_dict, f, allow_unicode=True)


def get_all_dict_recursively(hierarchy):
    parent_dict = {}

    for i in range(len(hierarchy) + 1):
        if not os.path.isfile(get_dict_path(hierarchy[:i])):
            create_translation_file(hierarchy[:i])
        new_dict = load_dict(hierarchy[:i])
        if new_dict:
            parent_dict.update(new_dict)
    return parent_dict


def create_translation_file(hierarchy):
    """

    :param hierarchy:
    :return:
    """
    if os.path.isfile(get_dict_path(hierarchy)):
        app.logger.info("File already exists for hierarchy: {}".format(hierarchy))
        return

    if not os.path.isdir("translation"):
        os.mkdir("translation")

    if len(hierarchy) == 0:
        parent_dict = {}
    else:
        parent_dict = get_all_dict_recursively(hierarchy[:-1])

    abs_path = AppConfig.target_domain + '/' + '/'.join(hierarchy)
    response = requests.get(abs_path)

    found_in_parent = set()
    not_found_in_parent = set()
    special_seperated = set()
    soup = bs(response.text, 'html.parser')
    for data in soup(["script", "style"]):
        data.decompose()

    for string in list(soup.stripped_strings) + [soup.title.string]:
        if AppConfig.skip_ascii and string.isascii():
            continue
        if len(string) > 3000 or len(string) < 2:
            continue
        if string not in parent_dict:
            if "|" in string:
                special_seperated.add(string)
                continue
            not_found_in_parent.add(string)
        else:
            found_in_parent.add(string)

    for string in special_seperated:

        # for the string which are separated by |, if all parts will be found in dict, add it to found
        string_part = string.split("|")
        all_part_found = True
        for part in string_part:
            part = part.strip()
            if not (part in parent_dict or part in found_in_parent or part in not_found_in_parent) \
                    and not (part.isascii() and AppConfig.skip_ascii):
                all_part_found = False
                break
        if all_part_found:
            found_in_parent.add(string)
        else:
            not_found_in_parent.add(string)
    # TODO: move common words in same level
    # if not found in parent exist in same level other translation file, remove it and add it to parent
    for string in not_found_in_parent:
        pass



    # print("not found in parent", not_found_in_parent)
    # print("found in parent", found_in_parent)
    save_dict(hierarchy, {k: "" for k in not_found_in_parent})
    if found_in_parent:
        save_dict(hierarchy, {k: "" for k in found_in_parent}, use_alternative=True)


def translate_string_with_dict(string, translation_dict):
    if AppConfig.skip_ascii and string.isascii():
        return string
    if string in translation_dict and translation_dict[string]:
        return translation_dict[string]

    if "|" in string:
        string_part = string.split("|")
        for part in string_part:
            if part.strip() in translation_dict and translation_dict[part.strip()]:
                translate = translation_dict[part.strip()]
                string = string.replace(part, translate)

                translation_dict[part.strip()] = ""
                string = string.replace(part, "")
            else:
                return ""
        return string
    return ""


def translate_content(soup, path):
    path = path.split('/')

    # remove empty string
    path = [x for x in path if x]

    translation_dict = get_all_dict_recursively(path)
    not_found_in_dict = set()

    for element in sorted(soup.find_all(string=True), key=lambda x: len(x.string.strip())):
        # if isinstance(element, Comment):
        #     continue
        # if isinstance(element, Doctype):
        #     continue
        # if isinstance(element, Script):
        #     continue
        if isinstance(element, (Comment, Doctype, Script, Stylesheet)):
            continue
        # if 'html' in element.string:
        #     print(element.__class__)
        original_string = element.string.strip()
        if not original_string:
            continue
        translation = translate_string_with_dict(original_string, translation_dict)
        if not translation:
            if original_string not in translation_dict:
                not_found_in_dict.add(original_string)
            continue
        element.replace_with(element.replace(original_string, translation))

    # translate title
    # if soup.title:
    #     translation = translate_string_with_dict(soup.title.string, translation_dict)
    #     if translation:
    #         soup.title.string = translation
    #     else:
    #         not_found_in_dict.add(soup.title.string)

    if len(not_found_in_dict) == 0:
        return soup

    if os.path.isfile(get_dict_path(path, use_alternative=True)):
        new_dict = load_dict(path, use_alternative=True).keys()

        if new_dict:
            not_found_in_dict.update(new_dict)

    save_dict(path, {k: "" for k in not_found_in_dict}, use_alternative=True)

    return soup


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
