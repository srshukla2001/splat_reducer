# save this as `splat_to_mesh.py`
import numpy as np
from plyfile import PlyData
import pyvista as pv
import os

def gaussian_splat_to_mesh(ply_path, output_path=None, splats_to_render=2000):
    """
    Convert a Gaussian Splatting .ply file to an .obj mesh file for visualization.
    
    Parameters:
    - ply_path: Path to input .ply file
    - output_path: Path for output .obj file (default: same as input with .obj extension)
    - splats_to_render: Maximum number of splats to convert (for performance)
    """
    # Default output path
    if output_path is None:
        output_path = os.path.splitext(ply_path)[0] + '_visualization.obj'
    
    print(f"Loading splats from: {ply_path}")
    ply = PlyData.read(ply_path)
    vertices = ply['vertex'].data
    vertices_np = np.array(vertices)
    
    # Extract position, scale, and color data
    # Position (x, y, z)
    if 'x' in vertices.dtype.names:
        positions = np.column_stack([
            vertices_np['x'].copy(), 
            vertices_np['y'].copy(), 
            vertices_np['z'].copy()
        ])
    else:
        # Fallback: assume first 3 fields are positions
        names = vertices.dtype.names[:3]
        positions = np.column_stack([vertices_np[names[0]], vertices_np[names[1]], vertices_np[names[2]]])
    
    # Scale (handle different naming conventions)
    scale = np.ones((len(positions), 3)) * 0.02  # Default scale
    
    scale_fields = []
    for pattern in ['scale_0', 'scale_1', 'scale_2', 'scale_x', 'scale_y', 'scale_z']:
        if pattern in vertices.dtype.names:
            scale_fields.append(pattern)
    
    if len(scale_fields) >= 3:
        # Apply exp to get actual scale (as per Gaussian Splatting format)
        scale = np.column_stack([
            np.exp(vertices_np[scale_fields[0]]),
            np.exp(vertices_np[scale_fields[1]]),
            np.exp(vertices_np[scale_fields[2]])
        ])
        # Normalize scale for better visualization
        scale = scale / np.percentile(scale.flatten(), 90) * 0.05
    
    # Color (r, g, b)
    if all(f in vertices.dtype.names for f in ['r', 'g', 'b']):
        colors = np.column_stack([vertices_np['r'], vertices_np['g'], vertices_np['b']])
    elif all(f in vertices.dtype.names for f in ['red', 'green', 'blue']):
        colors = np.column_stack([vertices_np['red'], vertices_np['green'], vertices_np['blue']])
    else:
        # Default color (blueish)
        colors = np.ones((len(positions), 3)) * [100, 150, 255]
    
    # Limit number of splats for performance
    if len(positions) > splats_to_render:
        indices = np.random.choice(len(positions), splats_to_render, replace=False)
        positions = positions[indices]
        scale = scale[indices]
        colors = colors[indices]
        print(f"  Rendering {splats_to_render} of {len(vertices_np)} total splats for performance")
    
    # Create a base sphere mesh
    sphere = pv.Sphere(theta_resolution=8, phi_resolution=6)
    
    # Combine all ellipsoids into one mesh
    all_points = []
    all_faces = []
    point_offset = 0
    
    for i in range(len(positions)):
        # Create a copy of the base sphere
        ellipsoid = sphere.copy()
        
        # Apply scaling to create ellipsoid shape
        ellipsoid.points *= scale[i] * 2.0  # Multiply for better visibility
        
        # Translate to position
        ellipsoid.points += positions[i]
        
        # Add points
        all_points.append(ellipsoid.points)
        
        # Add faces (adjust indices for combined mesh)
        faces = ellipsoid.faces.reshape(-1, 4)[:, 1:]  # Remove face vertex count
        faces += point_offset
        all_faces.append(faces)
        
        point_offset += len(ellipsoid.points)
    
    # Combine all meshes
    if all_points:
        combined_points = np.vstack(all_points)
        combined_faces = np.vstack(all_faces)
        
        # Create final mesh
        mesh = pv.PolyData(combined_points, faces=np.hstack([np.full((len(combined_faces), 1), 3), combined_faces]).flatten())
        
        # Save as OBJ
        mesh.save(output_path)
        print(f"✓ Mesh saved to: {output_path}")
        print(f"  Total vertices: {len(combined_points)}")
        print(f"  Total faces: {len(combined_faces)}")
        
        return output_path
    else:
        raise ValueError("No splats to convert")