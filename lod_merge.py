import sys
import numpy as np
from plyfile import PlyData, PlyElement

def main():
    if len(sys.argv) < 4:
        print("Usage: python lod_merge.py input.ply voxel_size output.ply")
        print("Example: python lod_merge.py input.ply 0.01 merged.ply")
        return

    input_file = sys.argv[1]
    voxel_size = float(sys.argv[2])
    output_file = sys.argv[3]

    print(f"Loading {input_file} ...")
    ply = PlyData.read(input_file)
    vertices = ply['vertex'].data
    data = np.array(vertices)

    print("Building voxel grid and merging...")

    # Extract positions (x, y, z)
    x = data['x']
    y = data['y']
    z = data['z']

    # Compute voxel index for each splat
    vox = np.floor(np.vstack((x, y, z)).T / voxel_size).astype(np.int32)
    
    # Convert voxel index to tuple so it can be a dict key
    vox_keys = [tuple(v) for v in vox]

    # Group indices by voxel
    voxel_dict = {}
    for i, key in enumerate(vox_keys):
        if key not in voxel_dict:
            voxel_dict[key] = []
        voxel_dict[key].append(i)

    print(f"Original splats: {len(data)}")
    print(f"Voxels created: {len(voxel_dict)} (merged result count)")

    # Prepare merged structured array
    dtype = data.dtype
    merged = np.empty(len(voxel_dict), dtype=dtype)

    # Merge logic: average all numeric fields
    for idx, (key, indices) in enumerate(voxel_dict.items()):
        subset = data[indices]
        for name in dtype.names:
            try:
                merged[name][idx] = np.mean(subset[name])
            except:
                # If non-numeric, just copy first value
                merged[name][idx] = subset[name][0]

    # Normalize normals if present
    if set(['nx','ny','nz']).issubset(dtype.names):
        norms = np.sqrt(merged['nx']**2 + merged['ny']**2 + merged['nz']**2) + 1e-9
        merged['nx'] /= norms
        merged['ny'] /= norms
        merged['nz'] /= norms

    # Write output
    vertex_el = PlyElement.describe(merged, 'vertex')
    PlyData([vertex_el], text=ply.text).write(output_file)

    print(f"Saved merged PLY → {output_file}")

if __name__ == "__main__":
    main()
