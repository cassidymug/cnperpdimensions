# Define DummyMetric outside of try-except to ensure it's always available
class DummyMetric:
    def labels(self, *args, **kwargs):
        return self
    def inc(self, *args, **kwargs):
        pass
    def observe(self, *args, **kwargs):
        pass
    def set(self, *args, **kwargs):
        pass

try:
    from prometheus_client import Counter, Histogram, Gauge
    
    # Generic report export metrics
    GENERIC_REPORT_REQUESTS = Counter(
        'generic_report_requests_total',
        'Total generic report export requests',
        ['format','cache_hit','backend']
    )

    GENERIC_REPORT_FLAT_ROWS = Histogram(
        'generic_report_flat_rows',
        'Flattened rows distribution',
        buckets=(10,50,100,250,500,1000,2000,3000,4000,5000)
    )

    GENERIC_REPORT_SIZE_BYTES = Histogram(
        'generic_report_payload_bytes',
        'Raw JSON payload size distribution',
        buckets=(1024,4096,16384,65536,131072,262144,524288,1048576,2097152)
    )
    
    GENERIC_REPORT_CACHE_SIZE = Gauge(
        'generic_report_cache_entries',
        'Current in-memory generic report cache entries'
    )
except ImportError:
    # Create dummy objects when prometheus_client is not available
    GENERIC_REPORT_REQUESTS = DummyMetric()
    GENERIC_REPORT_FLAT_ROWS = DummyMetric()
    GENERIC_REPORT_SIZE_BYTES = DummyMetric()
    GENERIC_REPORT_CACHE_SIZE = DummyMetric()

def set_cache_size(n: int):
    try:
        GENERIC_REPORT_CACHE_SIZE.set(n)
    except Exception:
        pass