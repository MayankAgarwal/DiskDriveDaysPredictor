import numpy as np
from GetDriveAttributes import GetDriveAttributes
import os
import re
import csv
from datetime import datetime
from datetime import timedelta

class ProcessData(object):
	"""
	"""

	def __init__(self):

		self.OBJ_DRIVE_ATTRIBUTES = GetDriveAttributes()
		
		self.DATA_PATH = os.path.join(
			os.path.abspath(
				os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
				), 
			'Data'
		)

		self.OUTPUT_DATA_PATH = os.path.join(
			os.path.abspath(os.path.dirname(os.path.dirname(__file__))),
			'Data'
		)

		self.SMART_ATTR_TO_DRIVES, self.DRIVES_BY_MFG, self.DRIVE_ATTRS, self.MFG_REPORTS_SAME_ATTRS = \
		self.OBJ_DRIVE_ATTRIBUTES.main()

		self.PROCESS_MANUFACTURERS = ['HGST'] #['HGST', 'Hitachi', 'Samsung', 'Toshiba', 'Western Digital']
		self.SMART_HEADER_REGEX = re.compile(r'(\d+)', re.I)
		self.SMART_HEADER_FORMAT = "smart_<<NUM>>_raw"
		
		self.CSV_DATE_COL = 'date'
		self.CSV_SERIAL_NO_COL = 'serial_number'
		self.CSV_MODEL_COL = 'model'
		self.CSV_FAILURE_COL = 'failure'

		self.DATE_FORMAT = '%Y-%m-%d'

		self.__visited_models = set([])
		self.__to_visit_models = set([])

	def __make_dirs(self, dirpath):
		"""Makes directories recursively

		:param: dirpath (str): path of the new directory structure to be created
		
		Returns:
			None
		"""

		try:
			os.makedirs(dirpath)
		except Exception as e:
			print str(e)
			pass

	def __get_smart_attr_header_val(self, smart_attr_description):
		"""Given the SMART Attribute description, returns the smart column header value
		as used in the CSV file

		:param: smart_attr_description (str) : Description of SMART attribute

		Returns:
			String : SMART attribute column header value
		"""

		match_obj = self.SMART_HEADER_REGEX.search(smart_attr_description)

		if not match_obj:
			return smart_attr_description

		smart_attr_number = match_obj.group(1)
		smart_header_val = self.SMART_HEADER_FORMAT.replace('<<NUM>>', smart_attr_number)
		return smart_header_val

	def __find_all_csv_files(self):
		"""Finds all CSV files in the Data folder and returns list of absolute paths to those files

		Returns:
			List(str): Absolute paths to all CSV files in the data directory
		"""

		csv_filelist = []

		for root, subdirs, files in os.walk(self.DATA_PATH):
			csv_files = filter(lambda x: x.endswith('csv'), files)
			csv_files = map(lambda x: os.path.join(root, x), csv_files)
			csv_filelist.extend(csv_files)

		return csv_filelist

	def __get_data_output_path(self, drive_model, make_path=True):
		""" Given a drive model, returns the path where the data for this model should be stored

		:param: drive_model (str): Drive model
		:param: make_path (bool): True if the method should create the path. False otherwise
								  Default: True

		Returns:
			str : Absolute path to the data folder which would contain the data for this drive model
		"""

		mfg = self.OBJ_DRIVE_ATTRIBUTES.get_drive_manufacturer(drive_model)
		output_path = os.path.join(self.OUTPUT_DATA_PATH, mfg, drive_model)

		if make_path:
			self.__make_dirs(output_path)

		return output_path

	def __get_header_indexes_for_drive_mfg(self, manufacturer, header_row):
		"""Finds the relevant SMART attribute header indexes in the CSV file for the particular manufacturer

		:param: manufacturer (str): Drive manufacturer
		:param: header_row (List(str)): Header row of the CSV file

		Returns:
			List(int) : 0-indexed column indexes which contain the SMART attributes the manufacturer reports
			List(str): SMART attributes that are associated with the indices
		"""

		smart_attrs = []
		header_indices = []

		for model, drive_attrs in self.DRIVE_ATTRS[manufacturer].iteritems():
			smart_attrs = drive_attrs
			break

		for attr in smart_attrs:
			attr_col_val = self.__get_smart_attr_header_val(attr)
			header_indices.append(
				header_row.index(attr_col_val)
			)

		return header_indices, smart_attrs

	def __read_csv_data_for_drive_model(self, csv_filepath, drive_model):
		"""Reads the data from a particular CSV file and for a particular model

		:param: csv_filepath (str) : File path to the CSV file that needs to be read
		:param: drive_model (str): Drive model for which the data needs to be read

		Returns:

		"""

		processed_result = {}

		f = open(csv_filepath, 'rb')
		reader = csv.reader(f)
		header_row = reader.next()

		manufacturer = self.OBJ_DRIVE_ATTRIBUTES.get_drive_manufacturer(drive_model)
		smart_attr_header_indices, smart_attrs = self.__get_header_indexes_for_drive_mfg(manufacturer, header_row)

		output_header = [self.CSV_DATE_COL, self.CSV_FAILURE_COL]
		output_header.extend(smart_attrs)

		output_header_indices = [header_row.index(self.CSV_DATE_COL), header_row.index(self.CSV_FAILURE_COL)]
		output_header_indices.extend(smart_attr_header_indices)

		model_index = header_row.index(self.CSV_MODEL_COL)
		serial_no_col = header_row.index(self.CSV_SERIAL_NO_COL)

		for datarow in reader:

			if datarow[model_index].lower() != drive_model.lower():
				continue

			serial_no = datarow[serial_no_col]
			data = [datarow[i] for i in output_header_indices]

			if serial_no not in processed_result:
				processed_result[serial_no] = []

			processed_result[serial_no].append(data)

		f.close()

		return processed_result, output_header

	def __save_csv_file(self, data, header, drive_model):
		"""Saves the data with header in a CSV file

		:param: data: Dictionary : serial_no: data for this disk drive
		:param: header: List(str): Header values for this drive model
		:param: drive_model: (str): Drive model

		Returns:
			Output folder path (str): Path to the output folder where the data is stored
									  A separate file is created for every serial number
		"""

		output_folder = self.__get_data_output_path(drive_model)

		for serial_no, sno_data in data.iteritems():
			output_filename = serial_no + ".csv"
			output_filepath = os.path.join(output_folder, output_filename)

			with open(output_filepath, 'w') as f:
				writer = csv.writer(f)
				temp_header, sno_data, temp = self.__update_data_to_include_classfication_output_labels(header, sno_data)
				if temp:
					print output_filepath
				writer.writerow(temp_header)
				writer.writerows(sno_data)

		return output_folder

	def __update_data_to_include_classfication_output_labels(self, headers, data):
		"""Updates the processed data to also include the classficiation output labels:
			1. op_fail_30 -> Will the drive fail in the next 30 days?
			2. op_fail_15 -> Will the drive fail in the next 15 days?
			3. op_fail_1 -> Will the drive fail in the next 1 day?

		:param: headers List(str): the headers of the CSV data
		:param: data : The data with each row representing a particular day and columns equals to headers

		Returns:
			headers List(str): Updated header values with classification labels included
			data List : Updated data to also include the classification labels
		"""
		temp = False
		fail_30, fail_15, fail_1 = timedelta(30), timedelta(15), timedelta(1)
		headers = list(headers)
		data = list(data)
		headers.extend(['op_fail_30', 'op_fail_15', 'op_fail_1'])

		date_index = headers.index(self.CSV_DATE_COL)
		fail_index = headers.index(self.CSV_FAILURE_COL)

		# Update date column to datetime object
		for datum in data:
			datum[date_index] = self.__parse_date(datum[date_index])

		i = 0
		for datum in data:
			try:
				datum.append(bool(filter(lambda x: (x[date_index] <= datum[date_index] + fail_30) and (int(x[fail_index]) == 1), data[i:])))
				if datum[-1]:
					temp = True
				datum.append(bool(filter(lambda x: (x[date_index] <= datum[date_index] + fail_15) and (int(x[fail_index]) == 1), data[i:])))
				datum.append(bool(filter(lambda x: (x[date_index] <= datum[date_index] + fail_1) and (int(x[fail_index]) == 1), data[i:])))
			except Exception as err:
				print err
			finally:
				i += 1
				datum[date_index] = self.__format_date(datum[date_index])

		return headers, data, temp

	def __parse_date(self, date_str):
		"""Parses string date and returns a datetime object

		:param: date_str (String): String representing date

		Returns:
			date (datetime obj): Date time object of the date
		"""

		try:
			date_obj = datetime.strptime(date_str, self.DATE_FORMAT)
		except Exception as _:
			return None
		else:
			return date_obj

	def __format_date(self, date_obj):
		"""Formats datetime object date into a string format

		:param: date_obj (datetime object): Datetime object of the date to be formatted into string

		Returns:
			date (string): String formatted date
		"""

		try:
			date_str = datetime.strftime(date_obj, self.DATE_FORMAT)
		except Exception as _:
			return None
		else:
			return date_str



	def main(self):
		"""Main method that processes all CSV files, segregates the data based on Model and Serial number,
		and stores the data in individual numpy data objects

		"""

		csv_filelist = self.__find_all_csv_files()

		for mfg in self.PROCESS_MANUFACTURERS:

			drives_by_manufacturer = self.DRIVES_BY_MFG[mfg]

			for drive_model in drives_by_manufacturer:

				model_data, model_header = {}, []

				for csv_file in csv_filelist[0:500]:

					print "Reading %s model data from file %s" % (drive_model, csv_file)

					csv_drive_model_data, csv_header = self.__read_csv_data_for_drive_model(csv_file, drive_model)
					
					for serial_no, data in csv_drive_model_data.iteritems():
						if serial_no not in model_data:
							model_data[serial_no] = data
						else:
							model_data[serial_no].extend(data)

						model_header = csv_header

				self.__save_csv_file(model_data, model_header, drive_model)



if __name__ == "__main__":
	test = ProcessData()
	test.main()