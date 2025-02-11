# async_benchmark.py
import time
from tasks import heavy_task

def async_benchmark(n_tasks=10):
    start_time = time.time()
    # Enqueue n_tasks asynchronously
    async_results = [heavy_task.delay() for _ in range(n_tasks)]
    # Wait for all tasks to complete and collect their results
    results = [res.get() for res in async_results]
    total_time = time.time() - start_time
    print(f"Asynchronous processing (via Celery): Processed {n_tasks} tasks in {total_time:.2f} seconds")
    return total_time

if __name__ == '__main__':
    async_benchmark(10)