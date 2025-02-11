# sync_benchmark.py
import time

def heavy_task_sync():
    # Simulate heavy processing (same as our Celery task)
    time.sleep(2)
    return "Done"

def sync_benchmark(n_tasks=10):
    start_time = time.time()
    results = []
    for _ in range(n_tasks):
        results.append(heavy_task_sync())
    total_time = time.time() - start_time
    print(f"Synchronous processing: Processed {n_tasks} tasks in {total_time:.2f} seconds")
    return total_time

if __name__ == '__main__':
    sync_benchmark(10)