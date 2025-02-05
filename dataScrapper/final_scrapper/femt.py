import aiohttp
import asyncio
import time
from datetime import datetime
import logging
from aiohttp import ClientTimeout
from typing import Dict, List, Optional
import pandas as pd
import csv
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

# Your token, organization, and bucket information
influxDB_Token = "605bc59413b7d5457d181ccf20f9fda15693f81b068d70396cc183081b264f3b"
org = "srs"
bucket = "srsran"

# Configuration
PROMETHEUS_URL = "http://localhost:9090"
INPUT_FILE = "allPromQuery.txt"
OUTPUT_FILE = "prometheus_combined.csv"
NUM_WORKERS = 20
BATCH_SIZE = 100
TIMEOUT = 10
RETRY_ATTEMPTS = 3
FETCH_INTERVAL = 1  # Seconds between fetch cycles

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class PrometheusClient:
    def __init__(self, base_url: str, timeout: int = TIMEOUT):
        self.base_url = base_url
        self.timeout = ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            connector=aiohttp.TCPConnector(
                limit=NUM_WORKERS * 2,
                ttl_dns_cache=300,
                force_close=False
            )
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def fetch_query(self, query: str, retries: int = RETRY_ATTEMPTS) -> Optional[float]:
        for attempt in range(retries):
            try:
                async with self.session.get(
                    f"{self.base_url}/api/v1/query",
                    params={"query": query},
                    raise_for_status=True
                ) as response:
                    result = await response.json()
                    if result.get('status') == 'success' and result.get('data', {}).get('result'):
                        return float(result['data']['result'][0]['value'][1])
                    return None
            except Exception as e:
                if attempt == retries - 1:
                    logging.error(f"Failed to fetch query '{query}': {str(e)}")
                    return None
                await asyncio.sleep(0.5 * (attempt + 1))

async def process_batch(client: PrometheusClient, queries: List[str]) -> Dict[str, Optional[float]]:
    tasks = [client.fetch_query(query) for query in queries]
    results = await asyncio.gather(*tasks)
    return dict(zip(queries, results))

async def fetch_influx_data() -> pd.DataFrame:
    dataFrame = {}
    uniqueFields = []
    async with InfluxDBClientAsync(url="http://10.40.1.5:8086", token=influxDB_Token, org=org) as client:
        query_api = client.query_api()
        query = '''
        from(bucket: "srsran")
          |> range(start: -60s)
          |> filter(fn: (r) => r["_measurement"] == "ue_info")
          |> filter(fn: (r) => r["testbed"] == "default")
        '''
        records = await query_api.query_stream(query)
        async for record in records:
            if record['_field'] not in uniqueFields:
                uniqueFields.append(record['_field'])
            key = f"{record['pci']}{record['rnti']}{record['_field']}"
            if key in dataFrame:
                dataFrame[key].append(float(record['_value']))
            else:
                dataFrame[key] = [float(record['_value'])]
        data = [{"key": key, "average": sum(values) / len(values)} for key, values in dataFrame.items()]
        return pd.DataFrame(data)

async def main():
    try:
        with open(INPUT_FILE, "r") as f:
            queries = [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        logging.error(f"Input file {INPUT_FILE} not found")
        return

    if not queries:
        logging.error("No queries found in input file")
        return

    async with PrometheusClient(PROMETHEUS_URL) as client:
        while True:
            start_time = time.time()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            all_results = {}

            for i in range(0, len(queries), BATCH_SIZE):
                batch = queries[i:i + BATCH_SIZE]
                batch_results = await process_batch(client, batch)
                all_results.update(batch_results)

            influxDF = await fetch_influx_data()
            prometheus_data = {query: all_results.get(query, '') for query in queries}

            with open(OUTPUT_FILE, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["Timestamp"] + list(prometheus_data.keys()) + list(influxDF.columns))
                if f.tell() == 0:  # Write header only if file is empty
                    writer.writeheader()

                for _, row in influxDF.iterrows():
                    combined_data = {
                        "Timestamp": timestamp,
                        **prometheus_data,
                        **row.to_dict()
                    }
                    writer.writerow(combined_data)

            elapsed = time.time() - start_time
            logging.info(f"Processed {len(queries)} queries in {elapsed:.2f}s")
            await asyncio.sleep(max(0, FETCH_INTERVAL - elapsed))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Shutting down gracefully...")
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
