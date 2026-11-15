import time

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np


class UWBWorkspaceSimulator:

	def __init__(self, anchors, noise_std=0.05):
		self.anchors = {k: np.array(v, dtype=float) for k, v in anchors.items()}
		self.noise_std = noise_std

	def generate_tilted_circle_trajectory(
		self, center, radius, tilt_deg, num_points=100, tilt_axis="x"
	):
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

		points = np.vstack((x, y, z))  # Shape: (3, N)

		# Convert tilt angle to radians
		alpha = np.radians(tilt_deg)

		# Rotation matrix
		if tilt_axis.lower() == "x":
			R = np.array([
				[1, 0, 0],
				[0, np.cos(alpha), -np.sin(alpha)],
				[0, np.sin(alpha), np.cos(alpha)],
			])
		elif tilt_axis.lower() == "y":
			R = np.array([
				[np.cos(alpha), 0, np.sin(alpha)],
				[0, 1, 0],
				[-np.sin(alpha), 0, np.cos(alpha)],
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
			step_data = {"step": step, "tag_position": tag_pos, "distances": {}}

			for anchor_id, anchor_pos in self.anchors.items():
				# True Euclidean distance
				true_dist = np.linalg.norm(tag_pos - anchor_pos)

				# Add realistic UWB noise
				if add_noise and self.noise_std > 0:
					measured_dist = true_dist + np.random.normal(0, self.noise_std)
					measured_dist = max(0.0, measured_dist)  # Distance cannot be negative
				else:
					measured_dist = true_dist

				step_data["distances"][anchor_id] = round(measured_dist, 4)

			simulation_log.append(step_data)

		return simulation_log

	def plot_workspace(self, trajectory):
		"""Visualizes the anchors and the tilted tag trajectory in 3D."""
		fig = plt.figure(figsize=(10, 8))
		ax = fig.add_subplot(111, projection="3d")

		# Plot Anchors
		for anchor_id, pos in self.anchors.items():
			ax.scatter(pos[0], pos[1], pos[2], color="red", s=100, marker="^")
			ax.text(
				pos[0],
				pos[1],
				pos[2] + 0.15,
				f"{anchor_id}\n({pos[0]},{pos[1]},{pos[2]})",
				color="darkred",
				fontsize=9,
				ha="center",
			)

		# Plot Tag Trajectory
		ax.plot(
			trajectory[:, 0],
			trajectory[:, 1],
			trajectory[:, 2],
			color="blue",
			linestyle="-",
			linewidth=2,
			label="Tag Path",
		)
		ax.scatter(
			trajectory[0, 0],
			trajectory[0, 1],
			trajectory[0, 2],
			color="green",
			s=80,
			label="Start Point",
		)

		# Labels and styling
		ax.set_xlabel("X (meters)")
		ax.set_ylabel("Y (meters)")
		ax.set_zlabel("Z (meters)")
		ax.set_title("UWB Workspace & Tilted Tag Trajectory")
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
		"A0": [0.0, 0.0, 0.0],
		"A1": [5.0, 0.0, 0.0],
		"A2": [5.0, 5.0, 0.0],
		"A3": [0.0, 5.0, 0.0],
	}

	sim = UWBWorkspaceSimulator(anchors=anchors, noise_std=0.05)

	# Derive strict X/Y boundaries from anchors, but allow Z to go higher than anchors
	anchor_coords = np.array(list(sim.anchors.values()))
	max_z = 4.0  # Ceiling height in meters (higher than anchor Z = 2.5)
	min_bounds = np.array([
		anchor_coords[:, 0].min(),
		anchor_coords[:, 1].min(),
		0.0,  # Floor height
	])
	max_bounds = np.array([
		anchor_coords[:, 0].max(),
		anchor_coords[:, 1].max(),
		max_z,  # Allows tags to go above anchor height
	])

	num_tages = 5
	tag_positions = {}
	tag_velocities = {}
	max_speed = 0.08  # Max meters per step
	for i in range(num_tages):
		tag_id = f"T{i}"
		# Start each tag strictly inside X/Y anchor bounds and [0, max_z]
		tag_positions[tag_id] = np.random.uniform(min_bounds, max_bounds)
		tag_velocities[tag_id] = np.random.uniform(-max_speed, max_speed, size=3)

	total_steps = 0
	sample_rate_hz = 30.0  # 30 Hz for smooth animation

	# --- Setup Live 3D Plot ---
	plt.ion()
	fig = plt.figure(figsize=(8, 6))
	ax = fig.add_subplot(111, projection="3d")

	# Plot static anchors
	for aid, apos in sim.anchors.items():
		ax.scatter(apos[0], apos[1], apos[2], c="red", marker="^", s=100)
		ax.text(apos[0], apos[1], apos[2] + 0.1, aid, color="red")

	# Create live moving markers for each tag (no lines)
	tag_markers = {}
	for tag_id, pos in tag_positions.items():
		(marker,) = ax.plot(
			[pos[0]], [pos[1]], [pos[2]], "o", markersize=8, label=tag_id
		)
		tag_markers[tag_id] = marker

	ax.set_xlim(min_bounds[0], max_bounds[0])
	ax.set_ylim(min_bounds[1], max_bounds[1])
	ax.set_zlim(min_bounds[2], max_bounds[2])
	ax.set_xlabel("X (m)")
	ax.set_ylabel("Y (m)")
	ax.set_zlabel("Z (m)")
	ax.set_title("Live Multi-Tag UWB Smooth Random Movement")
	ax.legend()

	print("Running continuous UWB simulation with 3D display (Ctrl+C to stop)...")
	try:
		while True:
			print(f"--- Step {total_steps:05d} ---")
			for tag_id in tag_positions:
				# Smooth momentum: 90% previous velocity + 10% gentle random steering
				accel = np.random.normal(0.0, 0.015, size=3)
				tag_velocities[tag_id] = 0.90 * tag_velocities[tag_id] + accel

				# Cap speed so tags glide smoothly instead of darting
				speed = np.linalg.norm(tag_velocities[tag_id])
				if speed > max_speed:
					tag_velocities[tag_id] = (tag_velocities[tag_id] / speed) * max_speed

				next_pos = tag_positions[tag_id] + tag_velocities[tag_id]

				# Bounce smoothly off X/Y anchor boundaries and [0, max_z] vertical bounds
				for axis in range(3):
					if next_pos[axis] < min_bounds[axis]:
						next_pos[axis] = min_bounds[axis]
						tag_velocities[tag_id][axis] *= -1
					elif next_pos[axis] > max_bounds[axis]:
						next_pos[axis] = max_bounds[axis]
						tag_velocities[tag_id][axis] *= -1

				tag_positions[tag_id] = next_pos

				# Convert internal [x, y, z] position into distances to each anchor
				step_data = sim.compute_distances(
					np.array([tag_positions[tag_id]]), add_noise=True
				)[0]
				pos = step_data["tag_position"]
				dists = step_data["distances"]

				# Update live 3D marker position
				tag_markers[tag_id].set_data([pos[0]], [pos[1]])
				tag_markers[tag_id].set_3d_properties([pos[2]])

				# Final output: distance array [A0, A1, A2, A3] per tag
				dist_array = [dists[aid] for aid in sim.anchors]
				print(f"  [{tag_id}] {dist_array}")

			# Redraw canvas and pause (replaces time.sleep so GUI stays responsive)
			plt.pause(1.0 / sample_rate_hz)
			total_steps += 1
		time.sleep(0.1)
	except KeyboardInterrupt:
		print("\nSimulation stopped.")
		plt.ioff()
		plt.close()