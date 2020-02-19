
import MySQLdb
import pandas as pd
from datetime import datetime
import re
from openpyxl import load_workbook
from collections import Counter
import logging
import sys
from datetime import datetime, timedelta


to_datetime = datetime.now()
from_datetime = to_datetime - timedelta(hours=12)
fromDateTime = from_datetime.strftime("%Y-%m-%d %H:%M:%S")
toDateTime = to_datetime.strftime("%Y-%m-%d %H:%M:%S")

if to_datetime.hour >= 18:
	shift = "morning"
else:
	shift = "night"

print("shift===============",shift)
print("fromDateTime===============",fromDateTime)
print("toDateTime=================",toDateTime)


####################                DATABASE CONNECTION           ############################

user     = "gifto"
password  = ""
db_name = "myntra_wh"
db      = MySQLdb.connect("localhost", user, password, db_name)
cursor  = db.cursor()


############## query for counting number of qc_pass and qc_fail
FP_count_query =  "SELECT date(created_at) as QC_date , hour(created_at) AS Hour, IF(qc_result=1, 'Pass', 'Fail') AS Result, count(qc_result) AS Total FROM reports WHERE created_at >= %s AND created_at < %s GROUP BY 1,2,3"

############## query for counting number of NA's
NA_count_query = "SELECT date(created_at) as QC_date ,hour(created_at) AS HOUR, count(primary_type) AS NA_TOTAL FROM error_reasons WHERE primary_type = 'NA' AND created_at >= %s AND created_at < %s GROUP BY 1,2"

############## query for getting the NA reasons
NA_reasons_query = "SELECT error_desc FROM error_reasons WHERE primary_type = 'NA' AND created_at >= %s AND created_at <= %s"

############## query for getting the count of sent_to_wms
sent_to_WMS_query = "SELECT date(created_at) as qc_date, IF(sent_to_wms=1, 'Yes', 'No') as Reached_WMS, count(sent_to_wms) as Total from reports where created_at >= %s and  created_at < %s group by 1,2"



########### writing the two dataframes to excelsheet and saving it
writer = pd.ExcelWriter('myntra_report.xlsx', engine='xlsxwriter')

################ counting the number of pass and fail ############

rows_count = cursor.execute(FP_count_query ,(fromDateTime, toDateTime))
passed = {}
failed = {}

if rows_count > 0 :
	print("i m hereeeeeee")
	for index, item in enumerate(cursor.fetchall()):
		if item[2] == "Pass":
			passed[index] = { 
			'qc_date' : str(item[0]),
			'hour' : item[1],
			'pass_count' : item[3]
		 	}
		else:
			failed[index] = { 
			'qc_date' : str(item[0]),
			'hour' : item[1],
			'fail_count' : item[3]
		 	}

	Flag = True
	passed_data = pd.DataFrame(passed.values(), columns=['qc_date', 'hour', 'pass_count'])
	failed_data = pd.DataFrame(failed.values(), columns=['qc_date','hour', 'fail_count'])
	print(passed_data)
	print(failed_data)

	if passed_data.empty :
		FP_data = pd.DataFrame(failed.values(), columns=['qc_date','hour', 'fail_count'])

	elif failed_data.empty : 
		FP_data = pd.DataFrame(passed.values(), columns=['qc_date', 'hour', 'pass_count'])

	else:
		FP_data = pd.merge(passed_data,failed_data, on=['qc_date','hour'], how='outer')
		FP_data.fillna(0, inplace=True)
	
	print("============== FP data ====================")
	print(FP_data)

else:
	Flag = False
	FP_data = pd.DataFrame()
	FP_data["qc_date"] = 0
	FP_data["hour"] = 0
	FP_data["pass_count"] = 0
	FP_data["fail_count"] = 0


################## counting the number of NAs #########################


na_rows_count = cursor.execute(NA_count_query ,(fromDateTime, toDateTime))

total_na = {}

if na_rows_count > 0:
	for index, item in enumerate(cursor.fetchall()):
		total_na[index] = {'qc_date': str(item[0]),
		'hour' : item[1],
		'NA_total' : item[2]
		}


	NA_data = pd.DataFrame(total_na.values(), columns=['qc_date', 'hour', 'NA_total'])
	print("==============  NA data  ==================")
	print(NA_data)

	if Flag == True:

		Full_data = pd.merge(FP_data, NA_data, on=['qc_date','hour'], how='outer')
		if shift == 'morning':
			Full_data = Full_data.sort_values("hour")

		if shift == 'night':
			Full_data = Full_data.sort_values("qc_date")
		
		Full_data.fillna(0, inplace=True)

		Full_data["Total_count"] = Full_data["pass_count"] + Full_data["fail_count"] + Full_data["NA_total"]
		Full_data["pass_count"] = Full_data["pass_count"].astype(int)
		Full_data["fail_count"] = Full_data["fail_count"].astype(int)
		Full_data["NA_total"] = Full_data["NA_total"].astype(int)
		Full_data["Total_count"] = Full_data["Total_count"].astype(int)

		Full_data["NA %"] = (Full_data["NA_total"] * 100) / Full_data["Total_count"]
		Full_data["location"] = "bilashpur"

		print("==============  Full_data ==================")
		print(Full_data)


		######################### pass percent, fail percent, NA_percent for given time frame

		sum_NA_total = Full_data["NA_total"].sum()
		sum_pass_count = Full_data["pass_count"].sum()
		sum_fail_count = Full_data["fail_count"].sum()
		sum_total_count = Full_data["Total_count"].sum()
		NA_percent = (sum_NA_total*100)/sum_total_count
		QC_pass_percent = (sum_pass_count*100)/sum_total_count
		QC_fail_percent = (sum_fail_count*100)/sum_total_count


		TotalSum = pd.DataFrame()
		TotalSum['NA_percent']= [NA_percent]
		TotalSum['QC_pass_percent']= [QC_pass_percent]
		TotalSum['QC_fail_percent'] = [QC_fail_percent]

		print('============================= Total percentage of all pass, fail, na in given time =====================================')
		print(TotalSum)

		Full_data.to_excel(writer, sheet_name='Sheet1', index=False)  

		TotalSum.to_excel(writer, sheet_name='Sheet1', startcol=13, index=False)

	if Flag == False:
		NA_data["location"] = "bilashpur"
		
		if shift == 'morning':
			NA_data = NA_data.sort_values("hour")
		
		if shift == 'night':
			NA_data = NA_data.sort_values("qc_date")

		NA_data.to_excel(writer, sheet_name='Sheet1', index=False)


else:
	
	FP_data["NA_total"] = 0
	FP_data['Total_count'] = FP_data['pass_count'] + FP_data['fail_count'] + FP_data["NA_total"]
	
	if FP_data.empty:
		print("================== no FP_data and NA_data to show====================")
	else:
		FP_data["location"] = "bilashpur"
		sum_pass_count = FP_data["pass_count"].sum()
		sum_fail_count = FP_data["fail_count"].sum()
		sum_total_count = FP_data["Total_count"].sum()
		QC_pass_percent = (sum_pass_count*100)/sum_total_count
		QC_fail_percent = (sum_fail_count*100)/sum_total_count

		TotalSum = pd.DataFrame()
		TotalSum['QC_pass_percent']= [QC_pass_percent]
		TotalSum['QC_fail_percent'] = [QC_fail_percent]
		print('============================= Total percentage of all pass, fail, na in given time =====================================')
		print(TotalSum)

		if shift == 'morning':
			FP_data = FP_data.sort_values("hour")

		if shift == 'night':
			FP_data = FP_data.sort_values("qc_date")


		FP_data.to_excel(writer, sheet_name='Sheet1', index=False)
		TotalSum.to_excel(writer, sheet_name='Sheet1', startcol=7, index=False)





#################### NA reasons ########################

nareason_row_count = cursor.execute(NA_reasons_query ,(fromDateTime, toDateTime))
na_reasonsList = []

if nareason_row_count > 0:
	for reason in cursor.fetchall():
		na_reasonsList.append(reason[0])
	print("na_reasonsList================",na_reasonsList)


	################ splitting the data using "||" to get proper reasons
	newList = []

	for item in na_reasonsList:
	    new_item = item.split('||')[0]
	    newList.append(new_item)


	################ Removing the digits from the items in list
	def remove_digits(list): 
	    pattern = '[0-9]'
	    list = [re.sub(pattern, '', i) for i in list] 
	    return list

	digit_removed_list = remove_digits(newList)



	##### Removing special characters from the items in list 
	bad_chars = ["{", "}", "(", ")" , "'", ","]
	proper_reasons = []
	for items in digit_removed_list : 
	    for i in bad_chars : 
	        items = items.replace(i, '') 
	    proper_reasons.append(items)

	redundant_proper_reasons = []
	for items in proper_reasons:
		redundant_proper_reasons.append(items.strip())


	###### Getting all the unique na_resons with their count  
	c = Counter(redundant_proper_reasons)
	na_reason_dict = dict(c.items())

	print("na_reason_dict===================", na_reason_dict)    

	unique_na_reasons = pd.DataFrame(na_reason_dict.items(), columns=['reason', 'count'])
	print("============================= NA reasons with count =================================")
	print(unique_na_reasons)

	unique_na_reasons.to_excel(writer, sheet_name='Sheet1', startcol=9, index=False)




########### counting the number of sent_to_wms ########################

sent_to_wms_row_count = cursor.execute(sent_to_WMS_query ,(fromDateTime, toDateTime))

sent_to_wms_result = {}

if sent_to_wms_row_count > 0 :
	for index, item in enumerate(cursor.fetchall()):
		sent_to_wms_result[index] = { 
			'qc_date' : str(item[0]),
			'reached_wms' : item[1],
			'total_count' : item[2]
		 	}

	sentToWMS = pd.DataFrame(sent_to_wms_result.values(), columns=['qc_date', 'reached_wms', 'total_count'])
	sentToWMS = sentToWMS.sort_values("qc_date")

	print("============================= sent_to_wms count =================================")
	print(sentToWMS)

	sentToWMS.to_excel(writer, sheet_name='Sheet1', startcol=12, index=False)	




writer.save()
