#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup as BS
import re

class GetDriveAttributes(object):
	"""Loads and parses the BackBlaze's drive attribute webpage and returns the drive attributes for 
	every manufacturer. Also verifies if the SMART attributes are same for all drives from a manufacturer.
	"""

	def __init__(self):
		
		self.DRIVE_ATTR_HREF = "https://www.backblaze.com/blog-smart-stats-2014-8.html"
		self.DRIVE_NAME_MANUFAC_MAP = {
			"HGST": "hgst",
			"Hitachi": "hitachi",
			"Samsung": "samsung",
			"Seagate": "st",
			"Toshiba": "toshiba",
			"Western Digital": "wd"
		}
		self.SMART_ATTR_HEADER_REGEX = re.compile(r'SMART \d+.*Raw Value.*', re.I)
		self.SMART_ATTR_DRIVE_LIST_REGEX = re.compile(r'Reported by drive models', re.I)
		self.NON_TEXT_REGEX = re.compile(r'[^\w]')

	def __load_webpage(self):
		"""Loads and parses the webpage
		
		Returns:
		    BeautifulSoup object: Parsed webpage
		"""

		r = requests.get(self.DRIVE_ATTR_HREF)
		href_parsed = BS(r.text, "lxml")
		return href_parsed

	def __clean_drive_text(self, drive_text):
		"""Cleans the raw drive list to produce a list of all the drives

		Returns:
			List (str): a list of all the drives from the text

		"""

		drives = map(lambda x: x.strip(), drive_text.split(','))
		drives = map(lambda x: re.sub(self.NON_TEXT_REGEX, '', x), drives)
		return drives


	def __get_smart_attr_headers_params(self, href_parsed):
		"""Gets the raw SMART attribute elements along with the 
		list of drives that report the corresponding attribute

		Returns:
			Dictionary : SMART attribute and list of drives
		"""

		smart_attr_to_drive_list_map = {}

		h4_elements = href_parsed.find_all('h4')
		smart_attr_headers = filter(lambda x: self.SMART_ATTR_HEADER_REGEX.match(x.text), h4_elements)

		for smart_attr_header in smart_attr_headers:
			drives = smart_attr_header.find_next(string=self.SMART_ATTR_DRIVE_LIST_REGEX).parent.parent
			drives = drives.text.split(':')[1]
			smart_attr_to_drive_list_map[smart_attr_header.text] = self.__clean_drive_text(drives)

		return smart_attr_to_drive_list_map

	def main(self):
		""" Main function that loads and parses the webpage and returns the 
		SMART attribute to disk drive data

		Returns:
			Dictionary : SMART Attribute -> List of drives reporting the attribute
		"""

		parsed_href = self.__load_webpage()
		smart_attr_to_drive_list_map = self.__get_smart_attr_headers_params(parsed_href)
		return smart_attr_to_drive_list_map

if __name__ == "__main__":
	drive_data_obj = GetDriveAttributes()
	print drive_data_obj.main()
