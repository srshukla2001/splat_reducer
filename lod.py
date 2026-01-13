import sys
import numpy as np
from plyfile import PlyData, PlyElement

def main():
    if len(sys.argv) < 4:
        print("Usage: python lod.py input.ply keep_ratio output.ply")
        print("Example: python lod.py input.ply 0.25 out.ply")
        return

    input_file = sys.argv[1]
    keep_ratio = float(sys.argv[2])
    output_file = sys.argv[3]

    print(f"Loading {input_file} ...")
    ply = PlyData.read(input_file)


    vertices = ply['vertex'].data  
    vertices_np = np.array(vertices) 

    total = len(vertices_np)
    keep = int(total * keep_ratio)

    print(f"Total splats: {total}")
    print(f"Keeping {keep} splats ({keep_ratio*100:.1f}%) ...")

    idx = np.random.choice(total, keep, replace=False)
    reduced = vertices_np[idx]

    vertex_el = PlyElement.describe(reduced, 'vertex')

    PlyData([vertex_el], text=ply.text).write(output_file)

    print(f"Saved reduced PLY → {output_file}")

if __name__ == "__main__":
    main()
