// Holder for a printed 60 x 12.7 mm plate (tools in SOFTWARE/alpr/tools/generate_plates.py).
// Keeps the plate flat and perpendicular - important for ALPR. Glue the tab to the toy car.
plate_w = 60.5; plate_h = 13.2; depth = 0.8; frame = 1.5; tab = 8; $fn = 24;

difference() {
    union() {
        cube([plate_w + 2 * frame, plate_h + 2 * frame, 2.2]);
        translate([(plate_w + 2 * frame) / 2 - 10, -tab, 0]) cube([20, tab + 1, 1.2]);   // glue tab
    }
    translate([frame, frame, 2.2 - depth]) cube([plate_w, plate_h, depth + 1]);
}
