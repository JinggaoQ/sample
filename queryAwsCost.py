import json
import boto3

ce = boto3.client('ce')

def lambda_handler(event, context):
    print(event)
    accountId = event['accountId']
    startDay = event['startDay']
    endDay = event['endDay']
    
    #需要返回的数据定义
    charge = ''
    prepaid = ''
    tax =''
    postPaid=''
    
    # 1. 获取总费用 aws ce get-cost-and-usage --time-period Start=2021-07-01,End=2021-08-01 --granularity MONTHLY --metrics "UnblendedCost"
    total_cost_response = ce.get_cost_and_usage(TimePeriod = {'Start': startDay, 'End': endDay},
    Granularity = 'MONTHLY', Metrics = ['UNBLENDED_COST'],
    Filter={
        "Dimensions": {
            "Key": "LINKED_ACCOUNT",
            "Values": [
                accountId
            ]
          }
        })
        
    results = []
    results.extend(total_cost_response['ResultsByTime'])
    for val in results:
        #这里获得了总费用
        charge = val['Total']['UnblendedCost']['Amount']
        
    
    # 2. 获取月分摊费用 aws ce get-cost-and-usage --time-period Start=2021-07-01,End=2021-08-01 --granularity MONTHLY --metrics "AmortizedCost"
    monthly_amortized_cost_response = ce.get_cost_and_usage(TimePeriod = {'Start': startDay, 'End': endDay},
    Granularity = 'MONTHLY', Metrics = ['AMORTIZED_COST'],
    Filter={
        "Dimensions": {
            "Key": "LINKED_ACCOUNT",
            "Values": [
                accountId
            ]
          }
        })
    results2 = []
    results2.extend(monthly_amortized_cost_response['ResultsByTime'])
    for val in results2:
        #这里获得了月分摊费用
        prepaid = val['Total']['AmortizedCost']['Amount']
    
    # 3. 获取税费,后付费费用 RECORD_TYPE
    tax_postpaid_response = ce.get_cost_and_usage(TimePeriod = {'Start': startDay, 'End': endDay},
    GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}], Granularity = 'MONTHLY', Metrics = ['UNBLENDED_COST'],
    Filter={
        "Dimensions": {
            "Key": "LINKED_ACCOUNT",
            "Values": [
                accountId
            ]
          }
        })
    results3 = []
    results3.extend(tax_postpaid_response['ResultsByTime'])
    
    #税费keyName
    #taxKey = "tax"
    taxKey = "Budgets"
    # 后付费KeyName。比如Recurring reservation fee, Savings Plan Recurring Fee
    #postpaidKey = "recurring"
    postpaidKey = "CloudTrail"
    
    
    for itemList in results3:
        for item in itemList['Groups']:
            Keys = item['Keys']
            for key in Keys:
                if(key.find(taxKey)>-1):
                    #包含税费信息
                     tax = item['Metrics']['UnblendedCost']['Amount']
                     break
                 #包含后付费信息
                if(key.find(postpaidKey)>-1):
                     postPaid = item['Metrics']['UnblendedCost']['Amount']
                     break
            
        
    
    
    result = {}
    result['accountId'] = accountId
    result['date'] = startDay
    result['currency'] = "USD"
    result['charge'] = charge
    result['tax'] = tax
    result['Postpaid'] = postPaid
    result['Prepaid1'] = prepaid
    result['Prepaid2'] = prepaid
    result['Prepaid3'] = prepaid
    result['total_cost_response'] = total_cost_response
    result['monthly_amortized_cost_response'] = monthly_amortized_cost_response
    result['tax_postpaid_response'] = tax_postpaid_response
    
    response = json.dumps(result) 
    return {
        'statusCode': 200,
        'body': response
    }
