// Barrier post for an SG90 micro servo + barrier arm (IoT Garage, osoba 2/4)
// Print: PLA, 0.2 mm layers, 20 % infill, no supports (post upright, arm flat).
// Arm lower edge ends up ~50 mm above the floor (see alati/kamera_kalkulator.py).
part = "all";          // "post" | "arm" | "all"
lane_width = 133;      // from nacrt/dimenzije.md
arm_height = 50;       // floor -> lower edge of the arm
wall = 2;
$fn = 48;

// SG90 body 22.8 x 12.2 x 22.5 mm, tabs 32.3 mm wide, shaft offset 5.9 mm from one end
sg_l = 23.0; sg_w = 12.4; sg_tabs = 32.5; tab_t = 2.5;
post_w = sg_w + 2 * wall; post_l = sg_tabs + 6;
post_h = arm_height - 9;   // horn + arm sit on top of the servo shaft

module post() {
    difference() {
        union() {
            translate([-post_l / 2, -post_w / 2, 0]) cube([post_l, post_w, post_h]);
            translate([-post_l / 2 - 8, -post_w / 2 - 8, 0]) cube([post_l + 16, post_w + 16, 3]); // foot
        }
        // servo pocket (servo pushed in from the top, tabs rest on the rim)
        translate([-sg_l / 2, -sg_w / 2, post_h - 22]) cube([sg_l, sg_w, 30]);
        translate([-sg_tabs / 2, -sg_w / 2, post_h - tab_t]) cube([sg_tabs, sg_w, 10]);
        // screw holes for the tabs
        for (x = [-sg_tabs / 2 + 2.3, sg_tabs / 2 - 2.3]) translate([x, 0, post_h - 10]) cylinder(d = 1.8, h = 12);
        // cable exit at the bottom
        translate([-3, -post_w / 2 - 1, 3]) cube([6, wall + 2, 6]);
        // foot screw holes
        for (x = [-post_l / 2 - 4, post_l / 2 + 4]) for (y = [-post_w / 2 - 4, post_w / 2 + 4])
            translate([x, y, -1]) cylinder(d = 3.2, h = 5);
    }
}

module arm() {
    len = lane_width - 6;
    difference() {
        union() {
            hull() {
                cylinder(d = 10, h = 4);
                translate([len, -3, 0]) cube([1, 6, 4]);
            }
        }
        // pocket for the single-arm servo horn (glue or screw it in)
        hull() { translate([0, 0, 2]) cylinder(d = 7.2, h = 3); translate([15, 0, 2]) cylinder(d = 4.2, h = 3); }
        translate([0, 0, -1]) cylinder(d = 2.2, h = 6);      // horn screw
    }
    // red stripes are painted / taped on later; small tip weight block
    translate([len - 6, -3, 4]) cube([6, 6, 2]);
}

if (part == "post" || part == "all") post();
if (part == "arm" || part == "all") translate([0, 30, 0]) arm();
