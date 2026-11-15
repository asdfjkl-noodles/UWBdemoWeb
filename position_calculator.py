import time
import numpy as np
from scipy.optimize import least_squares
from simulator import UWBWorkspaceSimulator

# Define the anchor positions matching your simulator
anchors = {
    "A0": [0.0, 0.0, 0.0],
    "A1": [5.0, 0.0, 0.0],
    "A2": [5.0, 5.0, 0.0],
    "A3": [0.0, 5.0, 0.0],
}

# Initialize the simulator instance
sim = UWBWorkspaceSimulator(anchors=anchors, noise_std=0.05)

# Setup workspace boundary constraints (matching your simulator)
anchor_coords = np.array(list(sim.anchors.values()))
max_z = 4.0
min_bounds = np.array([anchor_coords[:, 0].min(), anchor_coords[:, 1].min(), 0.0])
max_bounds = np.array([anchor_coords[:, 0].max(), anchor_coords[:, 1].max(), max_z])

# Initialize random positions and velocities for the tags (matching simulator logic)
num_tags = 5
tag_positions = {}
tag_velocities = {}
max_speed = 0.08

for i in range(num_tags):
    tag_id = f"T{i}"
    tag_positions[tag_id] = np.random.uniform(min_bounds, max_bounds)
    tag_velocities[tag_id] = np.random.uniform(-max_speed, max_speed, size=3)

def objective_function(tag_pos, anchor_positions, measured_distances):
    """
    Calculates the residuals between the estimated distances from 'tag_pos' 
    to each anchor and the noisy measured distances.
    """
    residuals = []
    for anchor_name, measured_dist in measured_distances.items():
        anchor_pos = anchor_positions[anchor_name]
        calc_dist = np.linalg.norm(tag_pos - anchor_pos)
        residuals.append(calc_dist - float(measured_dist))
    return np.array(residuals)

# Main real-time simulation and estimation loop
total_steps = 0
print("--- Starting Real-Time Multilateration Tracking for Smooth Movement ---")

try:
    while True:
        print(f"\n=== Step {total_steps:05d} ===")
        
        for tag_id in tag_positions:
            # 1. Update physics (Smooth momentum & random steering from simulator)
            accel = np.random.normal(0.0, 0.015, size=3)
            tag_velocities[tag_id] = 0.90 * tag_velocities[tag_id] + accel

            speed = np.linalg.norm(tag_velocities[tag_id])
            if speed > max_speed:
                tag_velocities[tag_id] = (tag_velocities[tag_id] / speed) * max_speed

            next_pos = tag_positions[tag_id] + tag_velocities[tag_id]

            # Bounce off boundary walls
            for axis in range(3):
                if next_pos[axis] < min_bounds[axis]:
                    next_pos[axis] = min_bounds[axis]
                    tag_velocities[tag_id][axis] *= -1
                elif next_pos[axis] > max_bounds[axis]:
                    next_pos[axis] = max_bounds[axis]
                    tag_velocities[tag_id][axis] *= -1

            tag_positions[tag_id] = next_pos
            true_pos = next_pos

            # 2. Compute noisy UWB distances for this step
            step_data = sim.compute_distances(np.array([true_pos]), add_noise=True)[0]
            dists = step_data["distances"]

            # 3. Run Least-Squares Multilateration to estimate coordinate back from distances
            initial_guess = true_pos # Or use previous estimation for continuity
            result = least_squares(
                objective_function, 
                initial_guess, 
                args=(sim.anchors, dists)
            )
            estimated_pos = result.x

            # 4. Print Ground Truth vs Calculated Position comparison
            print(
                f" [{tag_id}] "
                f"True Pos: [{true_pos[0]:6.3f}, {true_pos[1]:6.3f}, {true_pos[2]:6.3f}] | "
                f"Calc Pos: [{estimated_pos[0]:6.3f}, {estimated_pos[1]:6.3f}, {estimated_pos[2]:6.3f}]"
            )
            time.sleep(0.1)
        total_steps += 1

except KeyboardInterrupt:
    print("\nCalculation stopped by user.")