# 3DGS LOD Generator (PLY Downsampler)

This script takes a single `.ply` file (e.g., 3D Gaussian Splatting output) and generates lower-density LOD versions by uniformly sampling splats while preserving all attributes.

---

## 📦 Requirements

Install Python dependencies:

```bash
pip install numpy plyfile
🧩 Usage
Basic syntax:

bash
Copy code
python lod.py <input_file> <keep_ratio> <output_file>
Parameters:

Argument	Description
input_file	Source .ply file (e.g., full-resolution GS output)
keep_ratio	Fraction of splats to keep (0.0–1.0)
output_file	Name of reduced .ply output

🏁 Examples
Generate a 75% density LOD:

bash
Copy code
python lod.py input.ply 0.75 lod75.ply
Generate a 50% density LOD:

bash
Copy code
python lod.py input.ply 0.5 lod50.ply
This produces:

matlab
Copy code
lod75.ply  → 75% of original splats
lod50.ply  → 50% of original splats
🧠 Notes
Works on very large PLY files (tested on 10M+ splats)

Preserves all Gaussian splat attributes

Perfect for building multi-LOD pipelines for WebGS, Unity, VR, etc.

📁 Output Structure
Output .ply file preserves:

Position (x,y,z)

Normals

Scale parameters

SH coefficients (f_dc/f_rest)

Opacity

Any custom attributes

🛠 Script
lod.py contains the exact logic for downsampling with attribute preservation.
