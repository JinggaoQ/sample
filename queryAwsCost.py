import json
import boto3

ce = boto3.client('ce')

def lambda_handler(event, context):
    # TODO implement
    print(event)
    accountId = event['accountId']
    startDay = event['startDay']
    endDay = event['endDay']
    
    # run a query against the cost api to retrieve the cost and usage reports
    response = ce.get_cost_and_usage(TimePeriod = {'Start': startDay, 'End': endDay},
    GroupBy=[{'Type': 'DIMENSION', 'Key': 'RECORD_TYPE'}], Granularity = 'MONTHLY', Metrics = ['AMORTIZED_COST'],
    Filter={
        "Dimensions": {
            "Key": "LINKED_ACCOUNT",
            "Values": [
                accountId
            ]
          }
        })
    return {
        'statusCode': 200,
        'body': response
    }
