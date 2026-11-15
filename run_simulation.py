import time
import numpy as np
from scipy.optimize import least_squares
import database
from simulator import UWBWorkspaceSimulator

def objective_function(tag_pos, anchor_positions, measured_distances):
    residuals = []
    for anchor_name, measured_dist in measured_distances.items():
        if anchor_name in anchor_positions:
            anchor_pos = anchor_positions[anchor_name]
            calc_dist = np.linalg.norm(tag_pos - anchor_pos)
            residuals.append(calc_dist - float(measured_dist))
    return np.array(residuals)

def main():
    database.init_db()
    default_anchors = {"A0": [0.0, 0.0, 0.0], "A1": [5.0, 0.0, 0.0], "A2": [5.0, 5.0, 0.0], "A3": [0.0, 5.0, 0.0]}
    default_tags = {
        "T0": {"tilt_deg": 20, "radius": 1.5, "center": [2.5, 2.5, 1.2]},
        "T1": {"tilt_deg": 60, "radius": 1.5, "center": [2.5, 2.5, 1.2]}
    }
    database.seed_default_data(default_anchors, default_tags)

    tag_positions = {}
    tag_velocities = {}
    max_speed = 0.08
    total_steps = 0

    print("--- Dynamic UWB Simulation & DB Logger Running ---")

    try:
        while True:
            db_anchors = database.get_anchors()
            db_tags = database.get_tags()

            if not db_anchors or not db_tags:
                print("Waiting for anchors/tags in database...")
                time.sleep(1.0)
                continue

            sim = UWBWorkspaceSimulator(anchors=db_anchors, noise_std=0.05)

            # Calculate workspace bounds dynamically from current DB anchors
            anchor_coords = np.array(list(db_anchors.values()))
            min_bounds = np.array([anchor_coords[:, 0].min(), anchor_coords[:, 1].min(), 0.0])
            max_bounds = np.array([anchor_coords[:, 0].max(), anchor_coords[:, 1].max(), 4.0])

            active_tag_ids = list(db_tags.keys())
            for tid in active_tag_ids:
                if tid not in tag_positions:
                    tag_positions[tid] = np.array(db_tags[tid]["center"], dtype=float)
                    tag_velocities[tid] = np.random.uniform(-0.05, 0.05, size=3)

            for tid in list(tag_positions.keys()):
                if tid not in db_tags:
                    del tag_positions[tid]
                    del tag_velocities[tid]

            for tag_id in active_tag_ids:
                accel = np.random.normal(0.0, 0.015, size=3)
                tag_velocities[tag_id] = 0.90 * tag_velocities[tag_id] + accel
                
                speed = np.linalg.norm(tag_velocities[tag_id])
                if speed > max_speed:
                    tag_velocities[tag_id] = (tag_velocities[tag_id] / speed) * max_speed

                next_pos = tag_positions[tag_id] + tag_velocities[tag_id]

                # Bounce smoothly off workspace boundaries so tags never leave the 3D view
                for axis in range(3):
                    if next_pos[axis] < min_bounds[axis]:
                        next_pos[axis] = min_bounds[axis]
                        tag_velocities[tag_id][axis] *= -1
                    elif next_pos[axis] > max_bounds[axis]:
                        next_pos[axis] = max_bounds[axis]
                        tag_velocities[tag_id][axis] *= -1

                tag_positions[tag_id] = next_pos
                true_pos = next_pos

                step_data = sim.compute_distances(np.array([true_pos]), add_noise=True)[0]
                dists = step_data["distances"]

                result = least_squares(objective_function, true_pos, args=(sim.anchors, dists))
                estimated_pos = result.x

                database.log_step(total_steps, tag_id, true_pos, estimated_pos, dists)
                print(f"[Step {total_steps:04d}] {tag_id} | True: {true_pos.round(2)} | Calc: {estimated_pos.round(2)}")

            total_steps += 1
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nSimulation stopped.")

if __name__ == "__main__":
    main()