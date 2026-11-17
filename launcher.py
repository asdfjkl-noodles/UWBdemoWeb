import subprocess
import sys
import time
import os

# List of all background and web scripts to run concurrently
SCRIPTS = [
    "run_simulation.py",
    "app.py",
    "viewer.py",
    "floorplan.py"
]

def main():
    processes = []
    print("==================================================")
    print("🚀 Launching Unified UWB Enterprise System...")
    print("==================================================")

    try:
        for script in SCRIPTS:
            if not os.path.exists(script):
                print(f"❌ Error: Could not find '{script}' in the current directory.")
                sys.exit(1)
            
            print(f"-> Starting {script}...")
            # Spawn each script as an independent background subprocess
            p = subprocess.Popen([sys.executable, script])
            processes.append(p)
            time.sleep(0.6) # Short stagger to let ports bind cleanly

        print("\n✨ All services are up and running!")
        print("--------------------------------------------------")
        print(" ⚙️ Admin Dashboard  : http://127.0.0.1:5000")
        print(" 🧊 3D Visualizer    : http://127.0.0.1:5001")
        print(" 🗺️ Floorplan Map    : http://127.0.0.1:5002")
        print("--------------------------------------------------")
        print("🛑 Press Ctrl+C in this terminal to shut down everything.\n")

        # Keep the launcher alive to monitor processes
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n🛑 Received shutdown signal (Ctrl+C). Stopping all services...")
        for p in processes:
            p.terminate() # Gracefully ask processes to stop
        
        # Wait for all processes to close out completely
        for p in processes:
            p.wait()
            
        print("👋 All UWB services stopped successfully. Goodbye!")

if __name__ == '__main__':
    main()