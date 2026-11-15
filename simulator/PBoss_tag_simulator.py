import time

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

class UWBWorkspaceSimulator:
	def __init__(self, anchors, noise_std=0.05):
	   
		self.anchors = {k: np.array(v, dtype=float) for k, v in anchors.items()}
		self.noise_std = noise_std

	def generate_tilted_circle_trajectory(self, center, radius, tilt_deg, num_points=100, tilt_axis='x'):
		
		"""
		Generates 3D coordinates for a circular path tilted at a given angle.
		
		:param center: [x, y, z] center of the circle.
		:param radius: Radius of the circle in meters.
		:param tilt_deg: Tilt angle in degrees.
		:param num_points: Number of discrete steps/samples along the circle.
		:param tilt_axis: Axis to tilt around ('x' or 'y').
		:return: Nx3 numpy array of tag positions.
		"""
		theta = np.linspace(0, 2 * np.pi, num_points, endpoint=False)
		
		# Base circle in the XY plane centered at origin
		x = radius * np.cos(theta)
		y = radius * np.sin(theta)
		z = np.zeros_like(theta)
		
		points = np.vstack((x, y, z)) # Shape: (3, N)
		
		# Convert tilt angle to radians
		alpha = np.radians(tilt_deg)
		
		# Rotation matrix
		if tilt_axis.lower() == 'x':
			R = np.array([
				[1, 0, 0],
				[0, np.cos(alpha), -np.sin(alpha)],
				[0, np.sin(alpha),  np.cos(alpha)]
			])
		elif tilt_axis.lower() == 'y':
			R = np.array([
				[ np.cos(alpha), 0, np.sin(alpha)],
				[ 0,             1, 0            ],
				[-np.sin(alpha), 0, np.cos(alpha)]
			])
		else:
			raise ValueError("tilt_axis must be 'x' or 'y'")
			
		# Apply rotation and translate to the desired center
		tilted_points = (R @ points).T + np.array(center, dtype=float)
		return tilted_points

	def compute_distances(self, trajectory, add_noise=True):
		"""
		Computes distance from each tag position in the trajectory to every anchor.
		
		:param trajectory: Nx3 array of tag coordinates.
		:param add_noise: Boolean to toggle Gaussian UWB ranging noise.
		:return: List of dictionaries containing step data and anchor distances.
		"""
		simulation_log = []
		
		for step, tag_pos in enumerate(trajectory):
			step_data = {
				'step': step,
				'tag_position': tag_pos,
				'distances': {}
			}
			
			for anchor_id, anchor_pos in self.anchors.items():
				# True Euclidean distance
				true_dist = np.linalg.norm(tag_pos - anchor_pos)
				
				# Add realistic UWB noise
				if add_noise and self.noise_std > 0:
					measured_dist = true_dist + np.random.normal(0, self.noise_std)
					measured_dist = max(0.0, measured_dist) # Distance cannot be negative
				else:
					measured_dist = true_dist
					
				step_data['distances'][anchor_id] = round(measured_dist, 4)
				
			simulation_log.append(step_data)
			
		return simulation_log

	def plot_workspace(self, trajectory):
		"""Visualizes the anchors and the tilted tag trajectory in 3D."""
		fig = plt.figure(figsize=(10, 8))
		ax = fig.add_subplot(111, projection='3d')
		
		# Plot Anchors
		for anchor_id, pos in self.anchors.items():
			ax.scatter(pos[0], pos[1], pos[2], color='red', s=100, marker='^')
			ax.text(pos[0], pos[1], pos[2] + 0.15, f"{anchor_id}\n({pos[0]},{pos[1]},{pos[2]})", 
					color='darkred', fontsize=9, ha='center')
			
		# Plot Tag Trajectory
		ax.plot(trajectory[:, 0], trajectory[:, 1], trajectory[:, 2], 
				color='blue', linestyle='-', linewidth=2, label='Tag Path')
		ax.scatter(trajectory[0, 0], trajectory[0, 1], trajectory[0, 2], 
				   color='green', s=80, label='Start Point')
		
		# Labels and styling
		ax.set_xlabel('X (meters)')
		ax.set_ylabel('Y (meters)')
		ax.set_zlabel('Z (meters)')
		ax.set_title('UWB Workspace & Tilted Tag Trajectory')
		ax.legend()
		
		# Equalize aspect ratio roughly so the circle doesn't look distorted
		all_coords = np.vstack([list(self.anchors.values()), trajectory])
		max_range = (all_coords.max(axis=0) - all_coords.min(axis=0)).max() / 2.0
		mid = (all_coords.max(axis=0) + all_coords.min(axis=0)) * 0.5
		ax.set_xlim(mid[0] - max_range, mid[0] + max_range)
		ax.set_ylim(mid[1] - max_range, mid[1] + max_range)
		ax.set_zlim(max(0, mid[2] - max_range), mid[2] + max_range)
		
		plt.tight_layout()
		plt.show()


# ==========================================
# EXAMPLE USAGE & CONFIGURATION
# ==========================================

if __name__ == "__main__":
	anchors = {
	  "A0": [0.0, 0.0, 2.5],
	  "A1": [5.0, 0.0, 2.5],
	  "A2": [5.0, 5.0, 2.5],
	  "A3": [0.0, 5.0, 2.5],
  }

	sim = UWBWorkspaceSimulator(anchors=anchors, noise_std=0.05)
	num_tages = 5
	tag_trajectories = {}
	tag_angles = []
	for i in range(num_tages):
		tag_angles.append(20+i*40)
	# Generate the circular path once
	for i,tilt_angle in enumerate(tag_angles):
		tag_id = f"T{i}"
		tag_trajectories[tag_id] = {
			"trajectory": sim.generate_tilted_circle_trajectory(
				center=[2.5, 2.5, 1.2],
				radius=1.5,
				tilt_deg=tilt_angle,
				num_points=100,
			),
			"tilt_deg": tilt_angle
		}

	total_steps = 0
	sample_rate_hz = 10.0  # 10 Hz (0.1s per step)

	# --- Setup Live 3D Plot ---
	plt.ion()
	fig = plt.figure(figsize=(8, 6))
	ax = fig.add_subplot(111, projection="3d")

	# Plot static anchors
	for aid, apos in sim.anchors.items():
		ax.scatter(apos[0], apos[1], apos[2], c="red", marker="^", s=100)
		ax.text(apos[0], apos[1], apos[2] + 0.1, aid, color="red")

	# Plot static dashed trajectory paths & create live moving markers for each tag
	tag_markers = {}
	for tag_id, data in tag_trajectories.items():
		traj = data["trajectory"]
		tilt = data["tilt_deg"]
		ax.plot(
			traj[:, 0],
			traj[:, 1],
			traj[:, 2],
			"--",
			alpha=0.4,
			label=f"{tag_id} ({tilt}°)",
		)
		(marker,) = ax.plot(
			[traj[0, 0]], [traj[0, 1]], [traj[0, 2]], "o", markersize=8
		)
		tag_markers[tag_id] = marker

	ax.set_xlim(0, 5)
	ax.set_ylim(0, 5)
	ax.set_zlim(0, 3)
	ax.set_xlabel("X (m)")
	ax.set_ylabel("Y (m)")
	ax.set_zlabel("Z (m)")
	ax.set_title("Live Multi-Tag UWB Trajectory")
	ax.legend()

	total_steps = 0
	sample_rate_hz = 10.0

	print("Running continuous UWB simulation with 3D display (Ctrl+C to stop)...")
	try:
		while True:
			tag_logs = {
				tag_id: sim.compute_distances(data["trajectory"], add_noise=True)
				for tag_id, data in tag_trajectories.items()
			}

			for idx in range(100):
				print(f"--- Step {total_steps:05d} ---")
				for tag_id, data in tag_trajectories.items():
					step_data = tag_logs[tag_id][idx]
					pos = step_data["tag_position"]
					dists = step_data["distances"]
					tilt = data["tilt_deg"]

					# Update live 3D marker position
					tag_markers[tag_id].set_data([pos[0]], [pos[1]])
					tag_markers[tag_id].set_3d_properties([pos[2]])

					print(
						f"  [{tag_id} | {tilt:3d}°] Pos: [{pos[0]:7.4f}, {pos[1]:7.4f},"
						f" {pos[2]:7.4f}] | Distances: {dists}"
					)

				# Redraw canvas and pause (replaces time.sleep so GUI stays responsive)
				plt.pause(1.0 / sample_rate_hz)
				total_steps += 1

	except KeyboardInterrupt:
		print("\nSimulation stopped.")
		plt.ioff()
		plt.close()