import requests
import pandas as pd
import time
import json
import os
from datetime import datetime
import re
from xml.etree import ElementTree as ET
import fnmatch


#headers need to be declared in order for the SEC API to allow a connection
headers = {'User-Agent': "your-email-here@something.com",
			"Accept-Encoding": "gzip, deflate" }

fname = 'xml_13f'
desktop_path = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop/13F_Filings/')
#payload = {}

#check if output directory exists. if not, then create it
pExists = os.path.exists(desktop_path)
if not pExists:
	os.makedirs(desktop_path)
	print('Created output folder here: ' + desktop_path)
	print()

#req = requests.get('https://www.sec.gov/Archives/edgar/data/1067983/000119312512470800/d434976d13fhr.txt')
#response = requests.get("https://data.sec.gov/api/xbrl/companyconcept/CIK0001659047.json", headers=headers)
#response = requests.get("https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/Assets.json", headers=headers)

#retreive 13f-HR filing from the SEC API and save the text file version of the filing
#saving the text version because the naming is standardized
#CIK ID is the 10 digit CIK number with leading zeros plus "CIK"
def getPayload(cik):
	#converting to uppercase and removing any leading or trailing spaces
	cik = cik.upper().strip()
	if cik.startswith('CIK') and len(cik) == 13:
		#no formatting to be done
		pass
	elif cik.startswith('CIK') and len(cik) < 13:
		cik = cik.replace('CIK', '')
		cik = 'CIK' + cik.zfill(10)
	elif cik.startswith('CIK') and len(cik) > 13:
		raise Exception("Invalid CIK number")
	elif not cik.startswith('CIK') and len(cik) <= 10:
		cik = 'CIK' + cik.zfill(10)
	elif not cik.startswith('CIK') and len(cik) > 10:
		raise Exception("Invalid CIK number")
	else:
		raise Exception("Invalid CIK number")

	
	#formatting the CIK number in order to search archives
	cik_num = cik.replace('CIK', '')
	cik_num = cik_num.lstrip('0')

	url = "https://data.sec.gov/submissions/" + cik + ".json"

	response = requests.get(url, headers=headers).json()
	time.sleep(1)

	company_name = response["name"]
	company_name_formatted = re.sub(r'[\\/*?:"<>|]',"",company_name)
	company_name_formatted = company_name_formatted.replace(",", "")
	company_name_formatted = company_name_formatted.replace("'", "")
	company_name_formatted = company_name_formatted.replace(".", "")
	company_name_formatted = company_name_formatted.replace(" ", "_")

	filings = response["filings"]["recent"]
	filings_df = pd.DataFrame(filings)

	filings_df = filings_df[filings_df.form == "13F-HR"]

	access_number_unformatted = filings_df.accessionNumber.values[0]
	access_number = filings_df.accessionNumber.values[0].replace("-", "")
	file_name = access_number_unformatted + ".txt"

	#file_url = f"https://data.sec.gov/Archives/edgar/data/1659047/{access_number}/{access_number_unformatted}.txt"
	file_url = f"https://www.sec.gov//Archives/edgar/data/{cik_num}/{access_number}/{file_name}"

	#print(file_url)
	#print(filings_df)
	#print(filings_df.keys())
	#print(filings_df.filingDate.values[0])

	filing_date = filings_df.filingDate.values[0]

	req_content = requests.get(file_url, headers=headers).content.decode("utf-8")

	#write payload to text file. text file is the entire 13F-HR filing
	with open(desktop_path + fname + ".txt", "w") as f:
		f.write(req_content)

	#print(company_name_formatted)
	return filing_date, company_name_formatted


def give_options():
	print('Choose number from list or enter a CIK Number (example: CIK0001900946 or 1900946 or 0001900946)')
	print('1: CIK0001900946 - Carson Allaria')
	print('2: CIK0001659047 - Krilogy Financial')
	print('3: CIK0001927474 - Powers Advisory Group')
	#print('4: CIK0001800298 - Fair Square Financial Transferor')
	print('4: All of the above')
	print('0: Exit')
	choice = input('Choice: ')
	return choice

#takes 13F filing info as a list, the CIK IF of the company, filinf date of the 13F and the company name
#outputs to an excel file on the desktop
def output_to_excel(myList, cik, filing_date, company):
	securitiesDF = pd.DataFrame(myList)
	securitiesDF = securitiesDF.rename(columns={0:'Security', 1:'Title of Class', 2:'CUSIP', 3:'Value x1000', 4:'Number of Shares'})
	#print(securitiesDF.columns)
	today = datetime.now()
	current_date = str(today.year) + str(today.month).zfill(2) + str(today.day).zfill(2)
	filename = company + '_13F_' + filing_date + '.xlsx'

	#desktop_path = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop/' + filename) 
	export_path = desktop_path + filename

	securitiesDF.to_excel(export_path, sheet_name='13f', index=False)
	return export_path


#takes in a text filename that should contain xml
#xml within text file is then parsed and saved as an xml file containing only the 13F-HR filing
def extractXML(fname):
	f = open(fname + '.txt', 'r')
	lines = f.readlines()
	linenum = 0
	end_at = 0
	#string to designate the start of the 13F filing
	f13 = 'edgar/document/thirteenf/informationtable'

	for x in lines:
		if x.find(f13) != -1:
			linenum = lines.index(x)
			#print(x)
			
			for k in lines[linenum:]:
				#looks for the closing xml tag in order to properly end the file
				if fnmatch.fnmatch(k, '</*informationTable*'):
					xml_end = lines[linenum:].index(k)
					end_at = xml_end + linenum
					#print(lines[end_at])
					#exit the for loop once the marker for the end of file is found
					break

	#range of lines. need to parse the xml and extract values
	xml_13f = lines[linenum:end_at+1]
	f.close()

	#write the new 13F xml file, overwriting whatever was present before
	#overwriting is done to prevent buildup of past files
	with open(fname + '.xml', 'w') as fi:
		for j in xml_13f:
			fi.write(j)

#read the newly created xml file from the text file version of the 13f-HR filing
def parseXML(xmlfname):
	tree = ET.parse(xmlfname +'.xml')
	root = tree.getroot()
	finalList = []

	for child in root:
		tempList = []
		for leaf in child:
			#print(leaf.tag, leaf.text)
			if 'nameOfIssuer' in leaf.tag or 'cusip' in leaf.tag or 'value' in leaf.tag or 'titleOfClass' in leaf.tag:
				tempList.append(leaf.text)

			if 'shrsOrPrnAmt' in leaf.tag:
				for x in leaf:
					#print('		', x.tag, x.text)
					if 'sshPrnamt' in x.tag:
						tempList.append(x.text)
		finalList.append(tempList)

	return finalList

#Main program
#start by giving choices and run through different options
if __name__ == "__main__":
	choice = ''
	while choice != '0':
		choice = give_options()
		print()

		if choice == '0':
			quit()
		elif choice == '1':
			cik = ['CIK0001900946']
		elif choice == '2':
			cik = ['CIK0001659047']
		elif choice == '3':
			cik = ['CIK0001927474']
		#elif choice == '4':
		#	cik = ['CIK0001800298']
		elif choice == '4':
			cik = ['CIK0001900946', 'CIK0001659047', 'CIK0001927474']
		else:
			cik = [choice]

		for x in cik:
			time.sleep(2)
			try:
				#get the filing
				fnot = False
				xmlExists = os.path.exists(desktop_path + fname + '.txt')
				if xmlExists:
					last_update = os.path.getmtime(desktop_path + fname + '.txt')
				else:
					last_update = 0
				
				filing_date, company_name = getPayload(x)
				print('Most recent filing for ' + company_name + ' found from ' + filing_date)
				#check file modification time
				if os.path.getmtime(desktop_path + fname + '.txt') > last_update:
					pass
				else:
					fnot = True
					raise Exception('13F data may not be up to date. New file may not have been created.')
				#os.path.getmtime('file_path')
			except Exception as e:
				print('')
				if fnot:
					print(e)
				else:
					print(e)
					print('Invalid CIK, no 13F available or error retrieving data for CIK ' + x)
				print('')
				#using continue to go back to the start of the loop and ask again for input
				continue

			try:
				#get the necessary xml from the filing
				print('Extracting XML from text file')
				extractXML(desktop_path + fname)
			except Exception as e:
				print('')
				print('Error extracting xml from text file: ' + e)
				print('')
				continue

			try:
				#read the new xml file
				print('Reading XML from XML file')
				myList = parseXML(desktop_path + fname)
			except Exception as e:
				print('')
				print('Error reading xml from xml file: ' + e)
				print('')
				continue

			try:
				#create excel file
				#output_path = ''
				output_path = output_to_excel(myList, x, filing_date, company_name)
				print('Saving excel file to ' + output_path)
			except Exception as e:
				print('')
				print('Error creating excel file: ' + e)
				print('')
				continue
		print()
