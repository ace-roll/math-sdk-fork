"""Main file for generating results for Bonk Boi multiplier game."""

import sys
import os
import shutil
import gc
import time
# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from gamestate import GameState
from game_config import GameConfig
from game_optimization import OptimizationSetup
from optimization_program.run_script import OptimizationExecution
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs
from uploads.aws_upload import upload_to_aws

def cleanup_cache_and_temp():
    """Clean cache and temporary files for maximum speed"""
    print("🧹 Cleaning cache and temporary files...")
    
    # Clean Python cache
    cache_dirs = [
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache"
    ]
    
    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
            print(f"   ✅ Deleted: {cache_dir}")
    
    # Clean temporary simulation files
    temp_paths = [
        "library/temp_multi_threaded_files",
        "library/books/temp_*",
        "library/lookup_tables/temp_*"
    ]
    
    for temp_path in temp_paths:
        if os.path.exists(temp_path):
            if os.path.isdir(temp_path):
                shutil.rmtree(temp_path)
            else:
                os.remove(temp_path)
            print(f"   ✅ Deleted: {temp_path}")
    
    # Force memory cleanup
    gc.collect()
    
    # Additional cleanup for optimization
    import psutil
    process = psutil.Process()
    memory_before = process.memory_info().rss / 1024 / 1024  # MB
    print(f"   💾 Memory before cleanup: {memory_before:.1f} MB")
    
    # Force cleanup multiple times
    for i in range(3):
        gc.collect()
    
    memory_after = process.memory_info().rss / 1024 / 1024  # MB
    print(f"   ✅ Memory after cleanup: {memory_after:.1f} MB")
    print(f"   📉 Freed: {memory_before - memory_after:.1f} MB")

def monitor_memory():
    """Monitor memory usage"""
    try:
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        memory_gb = memory_mb / 1024
        print(f"💾 Current memory usage: {memory_mb:.1f} MB ({memory_gb:.2f} GB)")
        return memory_mb
    except ImportError:
        print("⚠️  psutil not installed - memory monitoring unavailable")
        return 0

if __name__ == "__main__":

    # ===== OPTIMAL PARAMETERS FOR 100M SIMULATIONS =====
    # System: 10 CPU cores, 16 GB RAM
    
    # Additional optimizations for speed
    gc.set_threshold(1000, 10, 10)  # Garbage collector optimization for 100M
    
    # Cleanup before launch
    cleanup_cache_and_temp()
    
    # Parameters for maximum speed 100M simulations
    num_threads = 10
    rust_threads = 10
    batching_size = 500_000
    compression = True
    profiling = False

    num_sim_args = {
        "base": int(10_000_000),
        "bonus1": int(10_000_000),  # Bonus game 1 (BONK_SPINS)
        "bonus2": int(10_000_000),  # Bonus game 2 (SUPER_BONK_SPINS)
    }

    run_conditions = {
        "run_sims": True,
        "run_optimization": False,
        "run_analysis": False,
        "upload_data": False,
    }
    target_modes = ["base", "bonus1", "bonus2"]

    print("🚀 Launching optimized 10M simulation")
    print(f"📊 Parameters:")
    print(f"   - Python threads: {num_threads}")
    print(f"   - Rust threads: {rust_threads}")
    print(f"   - Batch size: {batching_size:,}")
    print(f"   - Compression: {compression}")
    print(f"   - Simulations: {num_sim_args['base']:,}")
    # print(f"⏱️  Expected time: ~10-15 minutes")
    # print(f"💾 RAM usage: ~4-6 GB")

    config = GameConfig()
    gamestate = GameState(config)
    if run_conditions["run_optimization"] or run_conditions["run_analysis"]:
        optimization_setup_class = OptimizationSetup(config)

    start_time = time.time()  # Start time measurement

    if run_conditions["run_sims"]:
        print("\n⚡ Starting simulation...")
        monitor_memory()  # Monitor before start
        
        create_books(
            gamestate,
            config,
            num_sim_args,
            batching_size,
            num_threads,
            compression,
            profiling,
        )
        
        monitor_memory()  # Monitor after completion

    generate_configs(gamestate)
    monitor_memory()  # Monitor after config generation

    end_time = time.time()  # End time measurement
    total_time = end_time - start_time

    if run_conditions["run_optimization"]:
        OptimizationExecution().run_all_modes(config, target_modes, rust_threads)

    if run_conditions["upload_data"]:
        upload_items = {
            "books": True, 
            "lookup_tables": True,
            "force_files": True,
            "config_files": True,
        }
        upload_to_aws(
            gamestate,
            target_modes,
            upload_items,
        )
    
    print("✅ 10M simulation completed!")
    print(f"⏱️  Total time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
    print(f"📈 Speed: {num_sim_args['base']/total_time:,.0f} simulations/second")
