"""Export the model assembly (sklop_makete.scad): PNG views, one STL and a coloured GLB.

    python izvoz.py                 # everything
    python izvoz.py --slike         # only the PNG views (fast, ~20 s)
    python izvoz.py --3d            # only sklop_makete.stl + sklop_makete.glb (renders every colour group, ~minutes)

Needs OpenSCAD (>= 2021.01) on PATH; on Linux without a display it uses xvfb-run for the PNG views.
Only the Python standard library is used.

Outputs (next to this file):
    slike/*.png            views for the documentation
    sklop_makete.stl       whole model in one file (GitHub/GitLab show STL files as an interactive 3D view)
    sklop_makete.glb       whole model in colour (glTF 2.0: Windows 3D Viewer, Blender, https://gltf-viewer.donmccurdy.com)
"""

import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCAD = os.path.join(HERE, "sklop_makete.scad")

# name: camera, projection, extra -D options. Camera = eye x,y,z + centre x,y,z, or OpenSCAD's
# translate x,y,z + rotate x,y,z + distance (7 numbers).
VIEWS = {
    "sklop_pregled": ((335, 400, 20, 52, 0, 25, 2100), "p", []),
    "sklop_bez_zidova": ((344, 430, 20, 58, 0, 205, 1900), "p", ["show_walls=false"]),
    "sklop_tlocrt": ((344, 410, 0, 0, 0, 0, 2250), "o", []),
    "sklop_ulaz": ((420, 470, 200, 250, 250, 30), "p", []),
    "sklop_izlaz": ((590, 10, 215, 420, 300, 30), "p", []),
    "sklop_senzori": ((820, 520, 190, 540, 700, 95), "p", ["show_walls=false"]),
    "sklop_kamera": ((480, 430, 170, 244, 500, 120), "p", []),
}
# "what the camera sees": eye and target come from the model's echo (kamera_ulaz / kamera_izlaz)
CAMERA_VIEWS = {"pogled_kamere_ulaz": "kamera_ulaz", "pogled_kamere_izlaz": "kamera_izlaz"}


def openscad():
    exe = shutil.which("openscad") or shutil.which("openscad.exe") or shutil.which("openscad.com")
    if not exe:
        sys.exit("OpenSCAD not found on PATH (https://openscad.org/downloads.html)")
    return exe


def run_openscad(args, need_display=False):
    cmd = [openscad()] + args
    if need_display and sys.platform.startswith("linux") and not os.environ.get("DISPLAY") and shutil.which("xvfb-run"):
        cmd = ["xvfb-run", "-a"] + cmd
    return subprocess.run(cmd, cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def export_views(size):
    out_dir = os.path.join(HERE, "slike")
    os.makedirs(out_dir, exist_ok=True)
    for name, (cam, proj, defines) in VIEWS.items():
        path = os.path.join(out_dir, name + ".png")
        args = ["-o", path, "--imgsize=%d,%d" % size, "--camera=" + ",".join(str(c) for c in cam),
                "--projection=" + proj, "--colorscheme=Tomorrow"]
        for d in defines:
            args += ["-D", d]
        r = run_openscad(args + [SCAD], need_display=True)
        print("  %-20s %s" % (name, "ok" if r.returncode == 0 and os.path.exists(path) else "FAILED\n" + r.stdout[-800:]))
    for name, key in CAMERA_VIEWS.items():
        path = os.path.join(out_dir, name + ".png")
        eye, target = camera_pose(key)
        r = run_openscad(["-o", path, "--imgsize=%d,%d" % size, "--camera=" + ",".join("%.2f" % c for c in eye + target),
                          "--projection=p", "--colorscheme=Tomorrow", SCAD], need_display=True)
        print("  %-20s %s" % (name, "ok" if r.returncode == 0 and os.path.exists(path) else "FAILED\n" + r.stdout[-800:]))
    # catalogue of the purchased components
    path = os.path.join(out_dir, "komponente.png")
    r = run_openscad(["-o", path, "--imgsize=%d,%d" % size, "--camera=210,-615,560,150,15,10", "--projection=p",
                      "--colorscheme=Tomorrow", os.path.join(HERE, "komponente.scad")], need_display=True)
    print("  %-20s %s" % ("komponente", "ok" if r.returncode == 0 else "FAILED\n" + r.stdout[-800:]))


def camera_pose(key):
    """(eye, target) of a model camera, read from the echo of sklop_makete.scad."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "sklop.echo")
        run_openscad(["-o", path, SCAD])
        text = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    m = re.search(key + r" = \[\[([^\]]+)\], \[([^\]]+)\]\]", text)
    if not m:
        sys.exit("no '%s' in the echo of sklop_makete.scad" % key)
    return [float(v) for v in m.group(1).split(",")], [float(v) for v in m.group(2).split(",")]


# ------------------------------------------------------------------ 3D export
def colour_groups():
    """[(name, '#rrggbb')] from the BOJE table in komponente.scad."""
    text = open(os.path.join(HERE, "komponente.scad"), encoding="utf-8").read()
    table = text[text.index("BOJE = ["):text.index("];", text.index("BOJE = ["))]
    return re.findall(r'\["(\w+)",\s*"(#[0-9a-fA-F]{6})"\]', table)


def read_ascii_stl(path):
    tris = []
    with open(path, encoding="utf-8", errors="replace") as f:
        verts = []
        for line in f:
            line = line.strip()
            if line.startswith("vertex"):
                _, x, y, z = line.split()
                verts.append((float(x), float(y), float(z)))
                if len(verts) == 3:
                    tris.append(tuple(verts))
                    verts = []
    return tris


def export_groups(tmp):
    meshes = []
    for name, colour in colour_groups():
        path = os.path.join(tmp, name + ".stl")
        r = run_openscad(["-o", path, "--export-format", "asciistl", "-D", 'grupa="%s"' % name, SCAD])
        tris = read_ascii_stl(path) if r.returncode == 0 and os.path.exists(path) else []
        print("  %-14s %6d triangles" % (name, len(tris)))
        if tris:
            meshes.append((name, colour, tris))
    return meshes


def write_stl(path, meshes):
    count = sum(len(t) for _, _, t in meshes)
    with open(path, "wb") as f:
        f.write(b"IoT Garaza - sklop makete (mm)".ljust(80, b" "))
        f.write(struct.pack("<I", count))
        for _, _, tris in meshes:
            for a, b, c in tris:
                f.write(struct.pack("<3f", 0, 0, 0))
                for v in (a, b, c):
                    f.write(struct.pack("<3f", *v))
                f.write(b"\0\0")
    return count


def srgb_to_linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def write_glb(path, meshes):
    """Minimal glTF 2.0 binary: one indexed mesh per colour group, Y-up, metres."""
    gltf = {"asset": {"version": "2.0", "generator": "IoT Garaza izvoz.py"}, "scene": 0, "scenes": [{"nodes": []}],
            "nodes": [], "meshes": [], "materials": [], "buffers": [], "bufferViews": [], "accessors": []}
    blob = bytearray()

    def add_view(data, target):
        while len(blob) % 4:
            blob.append(0)
        gltf["bufferViews"].append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(data), "target": target})
        blob.extend(data)
        return len(gltf["bufferViews"]) - 1

    for name, colour, tris in meshes:
        index_of, positions, indices = {}, [], []
        for tri in tris:
            for x, y, z in tri:
                key = (round(x, 3), round(y, 3), round(z, 3))
                if key not in index_of:
                    index_of[key] = len(positions)
                    positions.append((x / 1000.0, z / 1000.0, -y / 1000.0))   # Z-up mm -> Y-up m
                indices.append(index_of[key])
        pos = struct.pack("<%df" % (3 * len(positions)), *[c for p in positions for c in p])
        idx = struct.pack("<%dI" % len(indices), *indices)
        mins = [min(p[i] for p in positions) for i in range(3)]
        maxs = [max(p[i] for p in positions) for i in range(3)]
        gltf["accessors"].append({"bufferView": add_view(pos, 34962), "componentType": 5126, "count": len(positions),
                                  "type": "VEC3", "min": mins, "max": maxs})
        gltf["accessors"].append({"bufferView": add_view(idx, 34963), "componentType": 5125, "count": len(indices),
                                  "type": "SCALAR"})
        r, g, b = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
        material = {"name": name, "doubleSided": True,
                    "pbrMetallicRoughness": {"baseColorFactor": [srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), 1.0],
                                             "metallicFactor": 0.3 if name == "srebrna" else 0.0,
                                             "roughnessFactor": 0.35 if name.startswith("auto") or name == "staklo" else 0.7}}
        if name.startswith("led_"):
            material["emissiveFactor"] = [srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b)]
        gltf["materials"].append(material)
        gltf["meshes"].append({"name": name, "primitives": [{"attributes": {"POSITION": len(gltf["accessors"]) - 2},
                                                             "indices": len(gltf["accessors"]) - 1,
                                                             "material": len(gltf["materials"]) - 1}]})
        gltf["nodes"].append({"name": name, "mesh": len(gltf["meshes"]) - 1})
        gltf["scenes"][0]["nodes"].append(len(gltf["nodes"]) - 1)
    while len(blob) % 4:
        blob.append(0)
    gltf["buffers"].append({"byteLength": len(blob)})
    js = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    js += b" " * (-len(js) % 4)
    with open(path, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(js) + 8 + len(blob)))
        f.write(struct.pack("<I4s", len(js), b"JSON") + js)
        f.write(struct.pack("<I4s", len(blob), b"BIN\0") + bytes(blob))


def export_3d():
    with tempfile.TemporaryDirectory() as tmp:
        meshes = export_groups(tmp)
    n = write_stl(os.path.join(HERE, "sklop_makete.stl"), meshes)
    write_glb(os.path.join(HERE, "sklop_makete.glb"), meshes)
    print("  sklop_makete.stl  %d triangles\n  sklop_makete.glb  %d colour groups" % (n, len(meshes)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slike", action="store_true", help="only the PNG views")
    ap.add_argument("--3d", dest="three_d", action="store_true", help="only the STL + GLB")
    ap.add_argument("--size", default="1600,1100", help="PNG size, e.g. 1600,1100")
    args = ap.parse_args()
    both = not args.slike and not args.three_d
    if args.slike or both:
        print("PNG views:")
        export_views(tuple(int(v) for v in args.size.split(",")))
    if args.three_d or both:
        print("3D export (every colour group is rendered separately):")
        export_3d()


if __name__ == "__main__":
    main()
