import aiohttp
import asyncio
import time
from datetime import datetime
import logging
from aiohttp import ClientTimeout
from typing import Dict, List, Optional

# Configuration
PROMETHEUS_URL = "http://localhost:9090"
INPUT_FILE = "usefulQuery.txt"
OUTPUT_FILE = "allPrometheus.csv"
NUM_WORKERS = 20 # Increased for better parallelization
BATCH_SIZE = 500   # Number of queries to process in each batch
TIMEOUT = 10     # Timeout in seconds
RETRY_ATTEMPTS = 3
FETCH_INTERVAL = 1 # Seconds between fetch cycles

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
                limit=NUM_WORKERS * 2,  # Double the number of workers for connection pool
                ttl_dns_cache=300,      # Cache DNS results for 5 minutes
                force_close=False       # Keep connections alive
            )
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def fetch_query(self, query: str, retries: int = RETRY_ATTEMPTS) -> Optional[float]:
        """Fetch a single query with retries"""
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
                await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff

async def process_batch(
    client: PrometheusClient,
    queries: List[str]
) -> Dict[str, Optional[float]]:
    """Process a batch of queries concurrently"""
    tasks = [client.fetch_query(query) for query in queries]
    results = await asyncio.gather(*tasks)
    return dict(zip(queries, results))

async def main():
    # Read and validate queries
    try:
        with open(INPUT_FILE, "r") as f:
            queries = [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        logging.error(f"Input file {INPUT_FILE} not found")
        return
    
    if not queries:
        logging.error("No queries found in input file")
        return

    # Initialize output file with headers
    with open(OUTPUT_FILE, "w") as f:
        headers = ["Timestamp"] + [
            ''.join(c if c.isalnum() else '_' for c in query)
            for query in queries
        ]
        f.write(",".join(headers) + "\n")

    # Main processing loop
    current_time=0
    end_time=600
    async with PrometheusClient(PROMETHEUS_URL) as client:
        while current_time < end_time:
            start_time = time.time()
            all_results = {}
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

            # Process queries in batches
            for i in range(0, len(queries), BATCH_SIZE):
                batch = queries[i:i + BATCH_SIZE]
                batch_results = await process_batch(client, batch)
                all_results.update(batch_results)

            # Write results to CSV
            with open(OUTPUT_FILE, "a") as f:
                row = [timestamp] + [
                    str(all_results.get(query, '')) for query in queries
                ]
                f.write(",".join(row) + "\n")

            # Calculate and log performance metrics
            elapsed = time.time() - start_time
            qps = len(queries) / elapsed
            logging.info(f"Processed {len(queries)} queries in {elapsed:.2f}s ({qps:.2f} queries/sec)")

            # Wait for next cycle, accounting for processing time
            wait_time = max(0, FETCH_INTERVAL - elapsed)
            await asyncio.sleep(wait_time)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Shutting down gracefully...")
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")