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
		self.UNIDENTIFIED_MANUFACTURER = "Unidentified"
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

		:param: drive_text (str): Drive model name.

		Returns:
			List (str): a list of all the drives from the text

		"""

		drives = map(lambda x: x.strip(), drive_text.split(','))
		drives = map(lambda x: re.sub(self.NON_TEXT_REGEX, '', x), drives)
		return drives

	def __get_drive_manufacturer(self, drive_model):
		"""Returns the manufacturer based on the drive model
		Uses the initial signature of the model to identify the manufacturer

		:param: drive_model (str): Drive model name

		Returns:
			String : manufacturer name
		"""

		drive_model = drive_model.lower()

		for mfg, signature in self.DRIVE_NAME_MANUFAC_MAP.iteritems():
			if drive_model.startswith(signature):
				return mfg

		return self.UNIDENTIFIED_MANUFACTURER


	def __get_smart_attr_headers_params(self, href_parsed):
		"""Gets the raw SMART attribute elements along with the 
		list of drives that report the corresponding attribute

		:param href_parsed (BeautifulSoup object): Parsed BackBlaze href.

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

	def __get_drives_grouped_by_mfg(self, attr_to_drive_map):
		"""Groups the list of drives grouped by manufacturer

		:param attr_to_drive_map (dict): SMART Attributes mapped to list of drive models.

		Returns:
			Dictionary : Manufacturer name -> List of drives supplied by manufacturer
		"""

		drives_by_manufacturer = {}

		for _, drives_list in attr_to_drive_map.iteritems():
			for drive in drives_list:
				mfg = self.__get_drive_manufacturer(drive)

				if mfg not in drives_by_manufacturer:
					drives_by_manufacturer[mfg] = set([])

				drives_by_manufacturer[mfg].add(drive)

		return drives_by_manufacturer

	def __manufacturer_reported_params(self, smart_attr_to_drive_list_map):
		"""Verifies if a SMART attribute is reported for all drives by a manufacturer
		If not, tracks the attributes not uniformly reported and then return this information

		:param smart_attr_to_drive_list_map (dict): SMART Attributes mapped to list of drive models.

		Returns:
			Dictionary : Manufacturer -> Drive -> List of attributes the drive reports
			Dictionary : Manufacturer -> (bool) "same_attributes" : does the mfg reports the same attr for all drives
										 (set of string) "uncommon_attributes" : attributes that are not uniformly reported 
		"""

		drive_attributes = {}
		manufacturer_reported_attributes = {}

		# Create a drive to the attributes it reports hashmap
		for attr, drives in smart_attr_to_drive_list_map.iteritems():
			for drive in drives:

				mfg = self.__get_drive_manufacturer(drive)
				if mfg not in drive_attributes:
					drive_attributes[mfg] = {}
				
				if drive not in drive_attributes[mfg]:
					drive_attributes[mfg][drive] = []
				drive_attributes[mfg][drive].append(attr)

		# Check if manufacturer reports the same parameters for all drives
		for mfg, drives in drive_attributes.iteritems():

			mfg_attrs = []
			mfg_reports_same_attrs = True
			uncommon_attributes = set([])

			for drive, attrs in drives.iteritems():
				if not mfg_attrs:
					mfg_attrs = attrs

				mfg_reports_same_attrs = set(mfg_attrs) == set(attrs)
				if not mfg_reports_same_attrs:
					uncommon_attributes.update(set(mfg_attrs).difference(set(attrs)))
					uncommon_attributes.update(set(attrs).difference(set(mfg_attrs)))

			manufacturer_reported_attributes[mfg] = {
				'same_attributes': mfg_reports_same_attrs,
				'uncommon_attributes': uncommon_attributes
			}

		return drive_attributes, manufacturer_reported_attributes
		
	def main(self):
		""" Main function that loads and parses the webpage and returns the 
		SMART attribute to disk drive data

		Returns:
			Dictionary : SMART Attribute -> List of drives reporting the attribute
			Dictionary : Manufacturer -> List of drives supplied by manufacturer
			Dictionary : Manufacturer -> Drive -> List of attributes the drive reports
			Dictionary : Manufacturer -> (bool) "same_attributes" : does the mfg reports the same attr for all drives
										 (set of string) "uncommon_attributes" : attributes that are not uniformly reported
		"""

		parsed_href = self.__load_webpage()

		smart_attr_to_drive_list_map = self.__get_smart_attr_headers_params(parsed_href)
		drives_by_manufacturer = self.__get_drives_grouped_by_mfg(smart_attr_to_drive_list_map)
		drive_attributes, mfg_reports_same_attrs = self.__manufacturer_reported_params(smart_attr_to_drive_list_map)
		
		return smart_attr_to_drive_list_map, drives_by_manufacturer, drive_attributes, mfg_reports_same_attrs

if __name__ == "__main__":
	drive_data_obj = GetDriveAttributes()
	import pprint
	pprint.pprint(drive_data_obj.main())
