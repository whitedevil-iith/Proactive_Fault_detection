import asyncio
import pandas as pd
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

# Your token, organization, and bucket information
token = "J-t1Bd6Xhn5Fj9Ooplyf4TpxN1tndPrSlWQq4sTVFfmsLqQLUvrJ_MwgQcGPDZoGsvhdFI1FIHDOzqcZBj8DKg=="
org = "srs"
bucket = "srsran"

async def influxDB():
    dataFrame = {}
    uniqueFields = []
    async with InfluxDBClientAsync(url="http://10.40.1.5:8086", token=token, org=org) as client:
        # Stream of FluxRecords
        query_api = client.query_api()
        
        # Flux query to get all records for the last 2 seconds
        query = '''
        from(bucket: "srsran")
          |> range(start: -60s)
          |> filter(fn: (r) => r["_measurement"] == "ue_info")
          |> filter(fn: (r) => r["testbed"] == "default")
        '''
        
        # Execute the query
        records = await query_api.query_stream(query)
        
        # Process records and populate dataFrame
        async for record in records:
            if(record['_field'] not in uniqueFields):
                uniqueFields.append(record['_field'])
            key = f"{record['pci']}{record['rnti']}{record['_field']}"
            if key in dataFrame:
                dataFrame[key].append(float(record['_value']))
            else:
                dataFrame[key] = [float(record['_value'])]
        print(uniqueFields)
        # Calculate the averages and create a pandas DataFrame
        data = [{"key": key, "average": sum(values) / len(values)} for key, values in dataFrame.items()]
        df = pd.DataFrame(data)

        return df

if __name__ == "__main__":
    df = asyncio.run(influxDB())
    print(df)
    print(f"Number of keys in the DataFra --classix
    nodme: {len(df)}")
 